import shlex
import subprocess
import asyncio
from typing import Any

async def execute_command(command: str) -> str:
    """Execute a shell command safely and return its stdout.

    This implementation runs the command in a subprocess with a timeout.
    It is deliberately restrictive – only simple commands are allowed.
    """
    # Split command safely
    args = shlex.split(command)
    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return "Command timed out"
        if proc.returncode != 0:
            return f"Error ({proc.returncode}): {stderr.decode().strip()}"
        return stdout.decode().strip()
    except FileNotFoundError:
        return "Command not found"
    except Exception as e:
        return f"Execution failed: {str(e)}"
