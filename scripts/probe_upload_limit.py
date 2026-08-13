"""Gate 0(e) — prove the upload cap rejects without buffering.

Sends an oversized body at a running server and samples, on an interval,
**both** the server process's RSS **and** the footprint of the temp directory
it spools to. Reports the peak of each.

Why both, and why the disk half is not optional
-----------------------------------------------
Starlette writes multipart *file* parts to a ``SpooledTemporaryFile``. Its
``max_part_size`` check sits under ``if self._current_part.file is None:`` in
``MultiPartParser.on_part_data`` — it applies to non-file parts only. So a file
part spills to disk past 1 MB with no ceiling.

An implementation that streams a 2 GB body straight to a temp file therefore
keeps RSS flat and **passes an RSS-only assertion** while writing 2 GB to /tmp.
That is precisely the failure mode ``BodySizeLimitMiddleware`` exists to
prevent, so a probe that cannot see it certifies the wrong thing.

Three cases, because the header is not the control
--------------------------------------------------
1. ``honest``      — Content-Length declared and accurate. The cheap early-out.
2. ``understated`` — Content-Length declared but far too small. The header check
                     passes; the byte counter must still stop it.
3. ``chunked``     — Transfer-Encoding: chunked, no Content-Length at all. The
                     header check never fires. Only the counter can catch this.

Usage
-----
    python -m scripts.probe_upload_limit --size 2GB --expect 413 \\
        --assert-peak-rss-under 256MB --assert-peak-disk-under 64MB

The server must already be running (``--url``), and this process must be able
to see it in the process table (``--pid``, or it is resolved from the port).
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from typing import Iterator, List, Optional

try:
    import psutil
except ImportError:  # pragma: no cover - dependency is declared in dev.txt
    print(
        "probe_upload_limit requires psutil (requirements/dev.txt).",
        file=sys.stderr,
    )
    raise

try:
    import httpx
except ImportError:  # pragma: no cover
    print("probe_upload_limit requires httpx (requirements/base.txt).", file=sys.stderr)
    raise


CHUNK = 1024 * 1024


# ---------------------------------------------------------------------------
# Size parsing / formatting
# ---------------------------------------------------------------------------

_UNITS = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}


def parse_size(text: str) -> int:
    raw = text.strip().upper()
    for suffix in ("GB", "MB", "KB", "B"):
        if raw.endswith(suffix):
            return int(float(raw[: -len(suffix)]) * _UNITS[suffix])
    return int(raw)


def human(n: int) -> str:
    for unit in ("GB", "MB", "KB"):
        if n >= _UNITS[unit]:
            return f"{n / _UNITS[unit]:.1f} {unit}"
    return f"{n} B"


# ---------------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------------


@dataclass
class Peaks:
    rss: int = 0
    disk: int = 0
    samples: int = 0
    baseline_disk: int = 0
    _rss_series: List[int] = field(default_factory=list)


def _dir_size(path: str) -> int:
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                # File vanished mid-walk — a spool file being cleaned up is the
                # expected case, not an error.
                continue
    return total


class Sampler(threading.Thread):
    """Polls RSS and temp-dir footprint until stopped."""

    def __init__(self, proc: psutil.Process, temp_dir: str, interval: float = 0.05):
        super().__init__(daemon=True)
        self.proc = proc
        self.temp_dir = temp_dir
        self.interval = interval
        self.peaks = Peaks(baseline_disk=_dir_size(temp_dir))
        self._stop = threading.Event()

    def run(self) -> None:
        while not self._stop.is_set():
            try:
                rss = self.proc.memory_info().rss
                # Children matter: a worker model spawns them, and the spool
                # file may be held by one.
                for child in self.proc.children(recursive=True):
                    try:
                        rss += child.memory_info().rss
                    except psutil.Error:
                        continue
            except psutil.Error:
                break

            disk = max(0, _dir_size(self.temp_dir) - self.peaks.baseline_disk)

            self.peaks.rss = max(self.peaks.rss, rss)
            self.peaks.disk = max(self.peaks.disk, disk)
            self.peaks.samples += 1
            self.peaks._rss_series.append(rss)

            self._stop.wait(self.interval)

    def stop(self) -> Peaks:
        self._stop.set()
        self.join(timeout=5)
        return self.peaks


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

BOUNDARY = "gatezeroeprobe"


def _multipart_stream(total_bytes: int, exam_id: str) -> Iterator[bytes]:
    head = (
        f"--{BOUNDARY}\r\n"
        f'Content-Disposition: form-data; name="exam_id"\r\n\r\n{exam_id}\r\n'
        f"--{BOUNDARY}\r\n"
        f'Content-Disposition: form-data; name="student_name"\r\n\r\nProbe\r\n'
        f"--{BOUNDARY}\r\n"
        f'Content-Disposition: form-data; name="student_roll_number"\r\n\r\nPROBE001\r\n'
        f"--{BOUNDARY}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="probe.pdf"\r\n'
        f"Content-Type: application/pdf\r\n\r\n"
    ).encode()
    yield head

    sent = 0
    payload = b"0" * CHUNK
    while sent < total_bytes:
        n = min(CHUNK, total_bytes - sent)
        yield payload[:n]
        sent += n

    yield f"\r\n--{BOUNDARY}--\r\n".encode()


def _send(url: str, size: int, mode: str, exam_id: str, timeout: float) -> tuple[int, str]:
    headers = {"Content-Type": f"multipart/form-data; boundary={BOUNDARY}"}

    if mode == "understated":
        # Deliberately a lie. The header check will wave this through.
        headers["Content-Length"] = "1024"
    elif mode == "chunked":
        # httpx uses chunked encoding for a generator body with no
        # Content-Length, which is the case the header check cannot see.
        pass
    elif mode == "honest":
        body_len = size + len(next(_multipart_stream(0, exam_id))) + len(BOUNDARY) + 8
        headers["Content-Length"] = str(body_len)
    else:
        raise ValueError(f"unknown mode {mode!r}")

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                url, content=_multipart_stream(size, exam_id), headers=headers
            )
            return response.status_code, response.text[:200]
    except httpx.RemoteProtocolError as exc:
        # The server closing the connection after refusing the body is an
        # acceptable outcome for the oversized case — it means it stopped
        # reading. Reported distinctly rather than silently treated as a pass.
        return -1, f"connection closed by server: {exc}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def resolve_pid(port: int) -> Optional[int]:
    for conn in psutil.net_connections(kind="inet"):
        if conn.laddr and conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
            return conn.pid
    return None


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000/submissions/upload")
    parser.add_argument("--size", default="2GB")
    parser.add_argument("--expect", type=int, default=413)
    parser.add_argument("--assert-peak-rss-under", default="256MB")
    parser.add_argument("--assert-peak-disk-under", default="64MB")
    parser.add_argument("--pid", type=int, default=None)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--temp-dir", default=tempfile.gettempdir())
    parser.add_argument("--exam-id", default="00000000-0000-0000-0000-000000000000")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument(
        "--modes",
        default="honest,understated,chunked",
        help="comma-separated subset of honest,understated,chunked",
    )
    args = parser.parse_args(argv[1:])

    size = parse_size(args.size)
    rss_limit = parse_size(args.assert_peak_rss_under)
    disk_limit = parse_size(args.assert_peak_disk_under)

    pid = args.pid or resolve_pid(args.port)
    if pid is None:
        print(
            f"Could not find a process listening on port {args.port}. "
            "Start the server, or pass --pid.",
            file=sys.stderr,
        )
        return 2

    try:
        proc = psutil.Process(pid)
    except psutil.NoSuchProcess:
        print(f"No such process: {pid}", file=sys.stderr)
        return 2

    free = shutil.disk_usage(args.temp_dir).free
    if free < size:
        print(
            f"WARNING: {human(free)} free in {args.temp_dir} but probing with "
            f"{human(size)}. If the server DOES buffer, it may hit ENOSPC "
            "before the assertion fires, which looks like a pass.",
            file=sys.stderr,
        )

    print(f"Gate 0(e) — upload limit probe")
    print(f"  target      {args.url}")
    print(f"  server pid  {pid}")
    print(f"  body size   {human(size)}")
    print(f"  temp dir    {args.temp_dir}")
    print(f"  limits      peak RSS < {human(rss_limit)}, peak disk < {human(disk_limit)}")
    print()

    failures = 0
    for mode in [m.strip() for m in args.modes.split(",") if m.strip()]:
        sampler = Sampler(proc, args.temp_dir)
        sampler.start()
        started = time.monotonic()

        status, body = _send(args.url, size, mode, args.exam_id, args.timeout)

        elapsed = time.monotonic() - started
        peaks = sampler.stop()

        status_ok = status == args.expect
        rss_ok = peaks.rss < rss_limit
        disk_ok = peaks.disk < disk_limit
        ok = status_ok and rss_ok and disk_ok

        print(f"[{mode}] {'PASS' if ok else 'FAIL'}  ({elapsed:.1f}s, {peaks.samples} samples)")
        print(f"    status     {status} (expected {args.expect}) {'ok' if status_ok else 'MISMATCH'}")
        print(f"    peak RSS   {human(peaks.rss)} {'ok' if rss_ok else 'OVER LIMIT'}")
        print(f"    peak disk  {human(peaks.disk)} {'ok' if disk_ok else 'OVER LIMIT'}")
        if not status_ok:
            print(f"    body       {body}")
        if not disk_ok:
            print(
                "    NOTE: peak disk over limit means the body was spooled "
                "before rejection — RSS staying flat does NOT make this a pass."
            )
        print()

        if not ok:
            failures += 1

    if failures:
        print(f"{failures} case(s) failed.", file=sys.stderr)
        return 1

    print("All cases passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
