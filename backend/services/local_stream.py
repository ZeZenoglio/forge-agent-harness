"""Local in-process stream service using asyncio queues.

Used as a fallback when ``REDIS_URL`` is not configured so the API runs
without any external dependencies during local development and testing.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any


class LocalStreamService:
    """Per-session asyncio queue-based event bus.

    Events are stored in a dict of queues keyed by session ID.  Consumers
    call :meth:`subscribe` to get an async generator that yields SSE-formatted
    strings.  Producers call :meth:`emit_event`.

    A sentinel ``None`` value is pushed to the queue when the stream is
    finished so that subscribers can exit cleanly.
    """

    _SENTINEL = object()

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue[Any]] = {}

    def _get_queue(self, session_id: str) -> asyncio.Queue[Any]:
        if session_id not in self._queues:
            self._queues[session_id] = asyncio.Queue()
        return self._queues[session_id]

    async def emit_event(self, session_id: str, event: dict[str, Any]) -> None:
        """Push *event* onto the queue for *session_id*."""
        q = self._get_queue(session_id)
        await q.put(event)
        # Automatically enqueue sentinel after finish/error events so the
        # subscriber generator exits without an extra call.
        if event.get("event_type") in ("finish", "error"):
            await q.put(self._SENTINEL)

    async def subscribe(self, session_id: str) -> AsyncGenerator[str]:
        """Yield SSE-formatted strings until the stream is finished."""
        q = self._get_queue(session_id)
        while True:
            item = await q.get()
            if item is self._SENTINEL:
                self._queues.pop(session_id, None)
                break
            yield f"data: {json.dumps(item)}\n\n"
