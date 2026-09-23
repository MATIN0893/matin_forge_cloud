import os
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .planner import generate_plan
from .broker import task_queue, add_task, get_next_task
from .command_handler import execute_command

app = FastAPI(title="MATIN FORGE Cloud Clone")

class PlanRequest(BaseModel):
    prompt: str

class TaskRequest(BaseModel):
    description: str

class CommandRequest(BaseModel):
    command: str

@app.post("/plan")
async def plan_endpoint(request: PlanRequest):
    try:
        plan = await generate_plan(request.prompt)
        return {"plan": plan}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tasks")
async def create_task(request: TaskRequest):
    try:
        await add_task(request.description)
        return {"status": "queued"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks/next")
async def fetch_next_task():
    try:
        task = await get_next_task()
        if task is None:
            return {"task": None}
        return {"task": task}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/command")
async def command_endpoint(request: CommandRequest):
    try:
        result = await execute_command(request.command)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
