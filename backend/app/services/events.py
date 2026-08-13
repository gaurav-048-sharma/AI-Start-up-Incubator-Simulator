"""
EventBus — in-process pub/sub keyed by idea_id.

Design goals:
  * The workflow NEVER blocks on slow/absent WebSocket clients:
    publishes are fire-and-forget into bounded per-subscriber queues
    (drop-oldest on overflow — a live dashboard only cares about "now").
  * Late joiners get a bounded replay history, so refreshing the page
    mid-run reconstructs the full timeline.
  * Monotonic per-idea sequence numbers let the client de-duplicate
    replayed events after a reconnect.

For multi-process deployments swap this for Redis pub/sub behind the
same interface — nothing else needs to change.
"""

import asyncio
import time
from collections import defaultdict, deque
from typing import Any

QUEUE_SIZE = 1000
HISTORY_SIZE = 500


class EventBus:
    def __init__(self, history_size: int | None = None) -> None:
        size = history_size or HISTORY_SIZE
        self._subs: dict[str, set[asyncio.Queue]] = defaultdict(set)
        self._history: dict[str, deque] = defaultdict(lambda: deque(maxlen=size))
        self._seq: dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()

    async def publish(self, idea_id: str, type_: str, data: dict[str, Any] | None = None) -> dict:
        async with self._lock:
            self._seq[idea_id] += 1
            event = {
                "v": 1,
                "type": type_,
                "idea_id": idea_id,
                "seq": self._seq[idea_id],
                "ts": time.time(),
                "data": data or {},
            }
            self._history[idea_id].append(event)
            for queue in self._subs[idea_id]:
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:  # slow consumer — drop oldest, keep stream live
                    try:
                        queue.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                    queue.put_nowait(event)
        return event

    async def subscribe(self, idea_id: str) -> tuple[asyncio.Queue, list[dict]]:
        """Returns (queue, replay_history)."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=QUEUE_SIZE)
        async with self._lock:
            self._subs[idea_id].add(queue)
            replay = list(self._history[idea_id])
        return queue, replay

    async def unsubscribe(self, idea_id: str, queue: asyncio.Queue) -> None:
        async with self._lock:
            self._subs[idea_id].discard(queue)
            if not self._subs[idea_id]:
                del self._subs[idea_id]

    async def clear(self, idea_id: str) -> None:
        """Reset history when a workflow is re-launched."""
        async with self._lock:
            self._history[idea_id].clear()
            self._seq[idea_id] = 0


bus = EventBus()
