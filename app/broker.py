import asyncio
from typing import Optional

# Simple in‑memory async queue for demonstration. In production replace with Redis, RabbitMQ, etc.
_task_queue: asyncio.Queue = asyncio.Queue()

task_queue = _task_queue  # Exported for external inspection if needed

async def add_task(description: str) -> None:
    """Add a new task description to the queue."""
    await _task_queue.put(description)

async def get_next_task() -> Optional[str]:
    """Retrieve the next task from the queue, or ``None`` if empty."""
    try:
        return _task_queue.get_nowait()
    except asyncio.QueueEmpty:
        return None
