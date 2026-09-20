import json
from collections.abc import AsyncGenerator
from typing import Any

import redis.asyncio as redis


class StreamService:
    def __init__(self, redis_url: str = "redis://localhost:6380"):
        self.redis = redis.from_url(redis_url)  # type: ignore

    async def emit_event(self, session_id: str, event_data: dict[str, Any]) -> None:
        """Publish an event to a specific session's stream."""
        stream_name = f"agent_stream:{session_id}"
        await self.redis.xadd(stream_name, {"data": json.dumps(event_data)})

    async def subscribe(self, session_id: str) -> AsyncGenerator[str]:
        """Subscribe to a session stream and yield SSE formatted strings."""
        stream_name = f"agent_stream:{session_id}"
        last_id = "0"
        
        while True:
            try:
                # Block for 2 seconds waiting for new events
                messages = await self.redis.xread({stream_name: last_id}, count=1, block=2000)
                if not messages:
                    continue
                    
                for stream, events in messages:
                    for msg_id, msg_data in events:
                        last_id = msg_id
                        data_str = msg_data.get(b"data", b"").decode("utf-8")
                        yield f"data: {data_str}\n\n"
                        
                        # Stop if event is terminal
                        if '"event_type": "finish"' in data_str or '"event_type": "error"' in data_str:
                            return
            except Exception as e:  # noqa: BLE001
                yield f"data: {json.dumps({'event_type': 'error', 'content': str(e)})}\n\n"
                break
