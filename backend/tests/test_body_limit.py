"""Tests for the request body size limit.

These drive BodySizeLimitMiddleware directly at the ASGI layer rather than
through an endpoint. The point of the middleware is that it acts *before* any
parser sees the body, so testing it through a multipart endpoint would test the
multipart parser instead — and would pass for the wrong reason if the parser
happened to reject the request first.

The defect being guarded against (D12): the upload cap used to be
``await file.read()`` followed by a length check, so the entire body was
resident before it could be rejected.
"""

import pytest

from app.core.body_limit import BodySizeLimitMiddleware

LIMIT = 1024  # 1 KB, so the tests stay fast


async def _ok_app(scope, receive, send):
    """Minimal ASGI app that drains the body and returns 200."""
    body = b""
    while True:
        message = await receive()
        body += message.get("body", b"")
        if not message.get("more_body", False):
            break

    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"text/plain")],
        }
    )
    await send({"type": "http.response.body", "body": str(len(body)).encode()})


def _scope(method="POST", headers=None):
    return {
        "type": "http",
        "method": method,
        "path": "/submissions/upload",
        "headers": headers or [],
    }


async def _run(app, scope, chunks):
    """Drive an ASGI app with the given body chunks; collect sent messages."""
    queue = list(chunks)
    sent = []

    async def receive():
        if queue:
            return {
                "type": "http.request",
                "body": queue.pop(0),
                "more_body": bool(queue),
            }
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    await app(scope, receive, send)
    return sent


def _status(sent):
    for message in sent:
        if message["type"] == "http.response.start":
            return message["status"]
    return None


@pytest.mark.asyncio
async def test_under_limit_passes_through():
    app = BodySizeLimitMiddleware(_ok_app, max_body_bytes=LIMIT)
    sent = await _run(app, _scope(), [b"x" * 100])
    assert _status(sent) == 200


@pytest.mark.asyncio
async def test_declared_content_length_over_limit_is_rejected():
    """Fast path: reject on the header without reading the body at all."""
    app = BodySizeLimitMiddleware(_ok_app, max_body_bytes=LIMIT)
    headers = [(b"content-length", str(LIMIT * 10).encode())]

    body_was_read = False

    async def tripwire_receive():
        nonlocal body_was_read
        body_was_read = True
        return {"type": "http.request", "body": b"x", "more_body": False}

    sent = []

    async def send(message):
        sent.append(message)

    await app(_scope(headers=headers), tripwire_receive, send)

    assert _status(sent) == 413
    assert not body_was_read, "body must not be read when Content-Length already exceeds the cap"


@pytest.mark.asyncio
async def test_chunked_body_over_limit_is_rejected_without_content_length():
    """The real control.

    A chunked-transfer client sends no Content-Length, so the header check
    above never fires. The running byte counter must still stop the request.
    """
    app = BodySizeLimitMiddleware(_ok_app, max_body_bytes=LIMIT)
    chunks = [b"x" * 400] * 10  # 4000 bytes, no content-length header

    sent = await _run(app, _scope(headers=[]), chunks)
    assert _status(sent) == 413


@pytest.mark.asyncio
async def test_understated_content_length_is_still_rejected():
    """A lying Content-Length must not buy extra bytes."""
    app = BodySizeLimitMiddleware(_ok_app, max_body_bytes=LIMIT)
    headers = [(b"content-length", b"10")]
    chunks = [b"x" * 400] * 10

    sent = await _run(app, _scope(headers=headers), chunks)
    assert _status(sent) == 413


@pytest.mark.asyncio
async def test_counter_stops_early_rather_than_draining():
    """Enforcement must abort mid-stream, not after consuming everything.

    This is the property that makes the limit bounded in memory and disk: the
    middleware stops pulling once the cap is passed.
    """
    app = BodySizeLimitMiddleware(_ok_app, max_body_bytes=LIMIT)

    chunks_read = 0

    async def counting_receive():
        nonlocal chunks_read
        chunks_read += 1
        return {"type": "http.request", "body": b"x" * 400, "more_body": True}

    sent = []

    async def send(message):
        sent.append(message)

    await app(_scope(), counting_receive, send)

    assert _status(sent) == 413
    # 1KB cap / 400-byte chunks: exceeded on the third read.
    assert chunks_read == 3, f"drained {chunks_read} chunks instead of stopping at 3"


@pytest.mark.asyncio
async def test_get_requests_are_not_intercepted():
    app = BodySizeLimitMiddleware(_ok_app, max_body_bytes=LIMIT)
    sent = await _run(app, _scope(method="GET"), [b""])
    assert _status(sent) == 200
