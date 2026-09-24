import os
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

from .planner import generate_plan
from .broker import task_queue, add_task, get_next_task
from .command_handler import execute_command

# Initialize Telegram bot and dispatcher
bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
dp = Dispatcher()

# /status handler
@dp.message(Command(commands=["status"]))
async def status_handler(message: types.Message) -> None:
    await message.answer("⚒️ MATIN FORGE CLOUD (ОБЛАЧНЫЙ КУЗНЕЦ) В СТРОЮ! Работает 24/7 на Render")

# /start handler – forwards task description to Groq LLM (llama-3.3-70b-versatile)
@dp.message(Command(commands=["start"]))
async def start_handler(message: types.Message) -> None:
    args = message.get_args()
    if not args:
        await message.answer("Please provide a task description after /start.")
        return
    response = await _process_task_with_groq(args)
    await message.answer(response)

async def _process_task_with_groq(prompt: str) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    endpoint = os.getenv("GROQ_ENDPOINT", "https://api.groq.com/openai/v1/chat/completions")
    model = "llama-3.3-70b-versatile"
    if not api_key:
        return "GROQ_API_KEY not set."
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are an assistant that processes user tasks."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 1024,
    }
    import httpx
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(endpoint, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            return "No response from Groq."
        return choices[0]["message"]["content"].strip()

# FastAPI lifespan to run bot polling in background
@asynccontextmanager
async def lifespan(app: FastAPI):
    polling_task = asyncio.create_task(dp.start_polling(bot))
    yield
    await dp.stop_polling()
    polling_task.cancel()
    try:
        await polling_task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan, title="MATIN FORGE Cloud Clone")

# FastAPI request models
class PlanRequest(BaseModel):
    prompt: str

class TaskRequest(BaseModel):
    description: str

class CommandRequest(BaseModel):
    command: str

# FastAPI endpoints (unchanged)
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
