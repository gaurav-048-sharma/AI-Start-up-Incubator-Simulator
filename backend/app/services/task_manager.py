"""
Background task manager — keeps long-running AI workflows off the
request/response cycle without losing track of them.

Why not plain BackgroundTasks?
  * BackgroundTasks gives you no handle: you can't ask "is this idea
    already incubating?" — so a double-click launches the workflow twice
    and burns tokens twice.
  * asyncio.create_task alone leaks: without a strong reference the task
    can be garbage-collected mid-run, and exceptions vanish silently.

This registry solves both: strong references, per-key dedup, and a
done-callback that surfaces exceptions into the logs.

Scaling note: for multi-worker deployments move execution to Celery/arq
and keep this same interface as the enqueue facade.
"""

import asyncio
from typing import Coroutine

import structlog

logger = structlog.get_logger()

_tasks: dict[str, asyncio.Task] = {}


def is_task_running(key: str) -> bool:
    task = _tasks.get(key)
    return task is not None and not task.done()


def launch_task(key: str, coro: Coroutine) -> bool:
    """
    Launch `coro` as a named background task.
    Returns False (and closes the coroutine) if `key` is already running.
    """
    if is_task_running(key):
        coro.close()
        logger.info("Task already running — launch skipped", task=key)
        return False

    task = asyncio.create_task(coro, name=key)
    _tasks[key] = task

    def _on_done(t: asyncio.Task) -> None:
        if _tasks.get(key) is t:
            _tasks.pop(key, None)
        if t.cancelled():
            logger.info("Background task cancelled", task=key)
        elif t.exception() is not None:
            logger.error("Background task crashed", task=key, error=str(t.exception()))

    task.add_done_callback(_on_done)
    logger.info("Background task launched", task=key)
    return True


def cancel_task(key: str) -> bool:
    task = _tasks.get(key)
    if task is not None and not task.done():
        task.cancel()
        return True
    return False


def running_tasks() -> list[str]:
    return [k for k, t in _tasks.items() if not t.done()]
