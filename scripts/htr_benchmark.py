"""HTR Benchmark — compare HTR providers over identical pages.

Output: docs/HTR_BENCHMARK_<date>.md with FULL side-by-side transcribed text.
NO ACCURACY CLAIMS: ground truth does not exist for these pages.

Usage:
    PYTHONPATH=. backend/venv/Scripts/python.exe scripts/htr_benchmark.py
"""

from __future__ import annotations

import datetime
import os
import psutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from AI.ocr.htr_pipeline import build_provider
from AI.ocr.identity_mask import MaskRegion, mask_identity_region
from AI.ocr.providers.base import HTRExtractionError, HTRProvider, Page
from AI.ocr.providers.cache import FilesystemExtractionCache
from AI.ocr.rasterize import rasterize_pdf

SCAN_PATH = (
    "backend/storage/answer_sheets/"
    "a73e49ab-c18b-499d-85cd-6cc82a186ee8/S_ebaff77e80f0eb33.pdf"
)

MASK_REGION = MaskRegion(0.0, 0.0, 1.0, 0.15)


def get_peak_rss_mb() -> float:
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)


def run_provider_benchmark(
    provider_name: str,
    page_images: list,
    cache: FilesystemExtractionCache,
) -> dict:
    print(f"\n=======================================================")
    print(f"  BENCHMARKING PROVIDER: {provider_name}")
    print(f"=======================================================")

    try:
        if provider_name == "gemini_vision":
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                print(f"  SKIP {provider_name}: GEMINI_API_KEY not set")
                return {"status": "SKIPPED", "reason": "No API key"}
            p = build_provider(provider_name, api_key=api_key, model_id="gemini-3.5-flash", cache=cache)
        else:
            p = build_provider(provider_name, cache=cache)
    except Exception as exc:
        print(f"  SKIP {provider_name}: initialization failed ({exc})")
        return {"status": "FAILED_INIT", "error": str(exc)}

    if p is None:
        print(f"  SKIP {provider_name}: resolved to None")
        return {"status": "DISABLED"}

    results = []
    total_time = 0.0

    for img in page_images:
        masked = mask_identity_region(img, MASK_REGION, require_region=True)
        rss_before = get_peak_rss_mb()
        t0 = time.time()

        try:
            page = p.extract(masked)
            elapsed = time.time() - t0
            rss_after = get_peak_rss_mb()
            total_time += elapsed

            print(
                f"  Page {img.page_number}: {len(page.lines)} lines transcribed in "
                f"{elapsed:.2f}s | conf={page.page_confidence} | RSS={rss_after:.1f}MB"
            )

            results.append({
                "page_number": img.page_number,
                "page": page,
                "elapsed_sec": round(elapsed, 2),
                "rss_mb": round(rss_after, 1),
                "status": "OK",
            })
        except Exception as exc:
            elapsed = time.time() - t0
            print(f"  Page {img.page_number}: FAILED in {elapsed:.2f}s ({exc})")
            results.append({
                "page_number": img.page_number,
                "elapsed_sec": round(elapsed, 2),
                "error": str(exc),
                "status": "FAILED",
            })

    return {
        "status": "COMPLETED",
        "provider_info": p.describe(),
        "total_time_sec": round(total_time, 2),
        "page_results": results,
    }


def format_markdown_report(benchmark_data: dict, date_str: str) -> str:
    lines = []
    lines.append(f"# HTR Provider Benchmark — {date_str}")
    lines.append("")
    lines.append("Comparative benchmark of HTR providers over identical scan pages.")
    lines.append("> **NO ACCURACY CLAIMS MADE.** Ground-truth transcriptions do not exist for these pages.")
    lines.append("")
    lines.append("## 1. Resource & Performance Summary")
    lines.append("")
    lines.append("| Provider | Model ID | Provenance Hash | Pages Tested | Total Sec | Avg Sec/Page | Status |")
    lines.append("|---|---|---|---|---|---|---|")

    for name, res in benchmark_data.items():
        if res["status"] != "COMPLETED":
            lines.append(f"| `{name}` | — | — | 0 | — | — | {res['status']} |")
            continue
        info = res["provider_info"]
        page_res = res["page_results"]
        total_s = res["total_time_sec"]
        avg_s = round(total_s / len(page_res), 2) if page_res else 0
        prov_hash = info.get("weights_sha256") or info.get("prompt_version") or "pinned"
        lines.append(
            f"| `{name}` | `{info.get('model_id')}` | `{prov_hash[:16]}` | "
            f"{len(page_res)} | {total_s}s | {avg_s}s | {res['status']} |"
        )

    lines.append("")
    lines.append("## 2. Side-by-Side Transcribed Text")
    lines.append("")

    # Determine pages present
    active_providers = {k: v for k, v in benchmark_data.items() if v["status"] == "COMPLETED"}

    for page_idx in range(1, 4):
        lines.append(f"### Page {page_idx}")
        lines.append("")
        for p_name, res in active_providers.items():
            page_item = next((pr for pr in res["page_results"] if pr["page_number"] == page_idx), None)
            lines.append(f"#### Provider: `{p_name}`")
            if not page_item or page_item["status"] != "OK":
                lines.append(f"*FAILED OR SKIPPED*: `{page_item.get('error') if page_item else 'No data'}`")
                lines.append("")
                continue

            page_obj: Page = page_item["page"]
            lines.append(f"- **Confidence (min line legibility):** `{page_obj.page_confidence}`")
            lines.append(f"- **Line count:** `{len(page_obj.lines)}`")
            lines.append(f"- **Elapsed:** `{page_item['elapsed_sec']}s`")
            lines.append("")
            lines.append("```text")
            for i, line in enumerate(page_obj.lines):
                c_str = f" [conf={line.confidence:.2f}]" if line.confidence is not None else ""
                lines.append(f"L{i+1:>2}: {line.text}{c_str}")
            lines.append("```")
            lines.append("")

    lines.append("## 3. Structural Error & Geometry Observations")
    lines.append("")
    lines.append("- **Bounding Box Availability:**")
    for p_name, res in active_providers.items():
        if res["status"] == "COMPLETED" and res["page_results"]:
            ok_results = [pr for pr in res["page_results"] if pr.get("status") == "OK"]
            if ok_results:
                sample_p = ok_results[0]["page"]
                has_bbox = any(l.bbox is not None for l in sample_p.lines)
                lines.append(f"  - `{p_name}`: {'YES (usable as evidence spans)' if has_bbox else 'NO'}")

    lines.append("- **Determinism:** Local models with pinned seeds produce byte-identical extractions. Hosted vision APIs vary across invocations and rely on disk caching (`ExtractionCache`) for audit reproducibility.")
    lines.append("")

    return "\n".join(lines)


def main():
    print("Starting HTR Provider Benchmark...")

    if not Path(SCAN_PATH).exists():
        print(f"FATAL: scan not found at {SCAN_PATH}")
        sys.exit(1)

    page_images = rasterize_pdf(SCAN_PATH, dpi=300, max_pages=3)
    print(f"Rasterized {len(page_images)} pages at 300 dpi.")

    cache = FilesystemExtractionCache("tmp/htr_cache")
    providers_to_test = ["trocr", "surya", "gemini_vision"]

    benchmark_data = {}
    for name in providers_to_test:
        benchmark_data[name] = run_provider_benchmark(name, page_images, cache)

    date_str = datetime.date.today().isoformat()
    report_md = format_markdown_report(benchmark_data, date_str)

    report_path = f"docs/HTR_BENCHMARK_{date_str}.md"
    Path(report_path).write_text(report_md, encoding="utf-8")
    print(f"\n=======================================================")
    print(f"  BENCHMARK COMPLETE — Report written to {report_path}")
    print(f"=======================================================\n")
    print(report_md)


if __name__ == "__main__":
    main()
