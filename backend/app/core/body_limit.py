"""Request body size limit, enforced on the raw ASGI receive stream.

This is the actual upload size control. Everything downstream of it is either
advisory or too late:

* ``Content-Length`` is client-supplied. It can be wrong, and under
  ``Transfer-Encoding: chunked`` it is absent entirely, so a header check alone
  is walked straight past by any client that omits it.

* Starlette's ``max_part_size`` does not bound file uploads. In
  ``MultiPartParser.on_part_data`` the size check sits under
  ``if self._current_part.file is None:`` — it applies to *non-file* parts
  only. File parts go to a ``SpooledTemporaryFile(max_size=1MB)``, which spills
  to disk past 1 MB with no ceiling.

* A byte counter in the storage layer runs after ``await request.form()`` has
  already parsed the body, by which point an arbitrarily large upload has
  been written to the system temp directory. Peak RSS stays flat while peak
  *disk* does not — which is why the Gate 0(e) probe asserts both.

Counting bytes as they arrive on the receive channel is the only place where
the body can be rejected before it is stored anywhere.
"""

from __future__ import annotations

import logging
from typing import Awaitable, Callable, MutableMapping

logger = logging.getLogger("GradeMIND.BodyLimit")

Scope = MutableMapping[str, object]
Message = MutableMapping[str, object]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]

BODY_METHODS = frozenset({"POST", "PUT", "PATCH"})


class _BodyTooLarge(Exception):
    """Internal signal: the receive stream exceeded the cap."""


class BodySizeLimitMiddleware:
    """Reject request bodies over ``max_body_bytes`` with 413.

    Pure ASGI rather than BaseHTTPMiddleware: BaseHTTPMiddleware buffers the
    request body to hand it to the endpoint, which would defeat the purpose.
    """

    def __init__(self, app, max_body_bytes: int):
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http" or scope.get("method") not in BODY_METHODS:
            await self.app(scope, receive, send)
            return

        # Cheap early-out for honest clients. Not the control — see module docstring.
        declared = _declared_length(scope)
        if declared is not None and declared > self.max_body_bytes:
            await _send_413(send, self.max_body_bytes)
            return

        received = 0
        response_started = False

        async def counting_receive() -> Message:
            nonlocal received
            message = await receive()
            if message.get("type") == "http.request":
                body = message.get("body", b"")
                received += len(body)  # type: ignore[arg-type]
                if received > self.max_body_bytes:
                    raise _BodyTooLarge()
            return message

        async def tracking_send(message: Message) -> None:
            nonlocal response_started
            if message.get("type") == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, counting_receive, tracking_send)
        except _BodyTooLarge:
            logger.warning(
                "Request body exceeded %d bytes on %s %s; rejected mid-stream",
                self.max_body_bytes,
                scope.get("method"),
                scope.get("path"),
            )
            if not response_started:
                await _send_413(send, self.max_body_bytes)
            # If the response had already started we cannot change the status.
            # Dropping the connection is the honest outcome; silently
            # completing would report success for a body we refused to read.


def _declared_length(scope: Scope) -> int | None:
    for name, value in scope.get("headers", []):  # type: ignore[union-attr]
        if name == b"content-length":
            try:
                return int(value)
            except ValueError:
                return None
    return None


async def _send_413(send: Send, limit_bytes: int) -> None:
    body = (
        b'{"detail":"Request body exceeds the maximum allowed upload size of '
        + str(limit_bytes // (1024 * 1024)).encode()
        + b' MB."}'
    )
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
