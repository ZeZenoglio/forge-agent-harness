"""Stream service that auto-selects Redis or local asyncio queues.

If ``REDIS_URL`` environment variable is set, a Redis Streams-backed
implementation is used.  Otherwise the in-process :class:`LocalStreamService`
is used so the API works with zero external dependencies during local dev.
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncGenerator
from typing import Any

from backend.services.local_stream import LocalStreamService

_local = LocalStreamService()


class StreamService:
    """Adaptive stream service.

    Delegates to Redis Streams when ``REDIS_URL`` is configured, or falls
    back to the in-process asyncio queue implementation.
    """

    def __init__(self) -> None:
        self._redis_url = os.getenv("REDIS_URL")
        self._redis: Any = None
        self._local = _local

        if self._redis_url:
            try:
                import redis.asyncio as redis

                self._redis = redis.from_url(self._redis_url)  # type: ignore[no-untyped-call]
            except ImportError:
                self._redis = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def emit_event(self, session_id: str, event_data: dict[str, Any]) -> None:
        """Publish an event to a specific session's stream."""
        if self._redis is not None:
            await self._redis_emit(session_id, event_data)
        else:
            await self._local.emit_event(session_id, event_data)

    async def subscribe(self, session_id: str) -> AsyncGenerator[str]:
        """Subscribe to a session stream and yield SSE-formatted strings."""
        if self._redis is not None:
            async for chunk in self._redis_subscribe(session_id):
                yield chunk
        else:
            async for chunk in self._local.subscribe(session_id):
                yield chunk

    # ------------------------------------------------------------------
    # Redis implementation
    # ------------------------------------------------------------------

    async def _redis_emit(self, session_id: str, event_data: dict[str, Any]) -> None:
        stream_name = f"agent_stream:{session_id}"
        await self._redis.xadd(stream_name, {"data": json.dumps(event_data)})

    async def _redis_subscribe(self, session_id: str) -> AsyncGenerator[str]:
        stream_name = f"agent_stream:{session_id}"
        last_id = "0"

        while True:
            try:
                messages = await self._redis.xread(
                    {stream_name: last_id}, count=1, block=2000
                )
                if not messages:
                    continue

                for _stream, events in messages:
                    for msg_id, msg_data in events:
                        last_id = msg_id
                        data_str = msg_data.get(b"data", b"").decode("utf-8")
                        yield f"data: {data_str}\n\n"

                        if (
                            '"event_type": "finish"' in data_str
                            or '"event_type": "error"' in data_str
                        ):
                            return
            except Exception as e:  # noqa: BLE001
                yield f"data: {json.dumps({'event_type': 'error', 'content': str(e)})}\n\n"
                break
