import os
import asyncio
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = "llama-3.1-8b-instant"

# Initialise bot and dispatcher
bot = Bot(token=TOKEN) if TOKEN else None
dp = Dispatcher()

async def call_groq(prompt: str) -> str:
    """Send a prompt to Groq and return the assistant's reply."""
    if not GROQ_KEY:
        return "⚠️ GROQ_API_KEY не задан в переменных окружения Render!"
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "Ты — MATIN FORGE CLOUD, облачный ассистент и кузнец инструментов. Отвечай кратко, емко и по коду."},
            {"role": "user", "content": prompt},
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            return f"⚠️ Ошибка Groq ({resp.status_code}): {resp.text}"
    except Exception as e:
        return f"⚠️ Ошибка подключения к Groq: {e}"

async def get_models() -> str:
    """Fetch the list of available models from Groq's /v1/models endpoint.

    Returns a formatted string with model IDs or an error message.
    """
    if not GROQ_KEY:
        return "⚠️ GROQ_API_KEY не задан в переменных окружения Render!"
    url = os.getenv(
        "GROQ_MODELS_ENDPOINT", "https://api.groq.com/openai/v1/models"
    )
    headers = {"Authorization": f"Bearer {GROQ_KEY}"}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("data", [])
                if not models:
                    return "⚠️ Нет доступных моделей."
                model_ids = [m.get("id", "unknown") for m in models]
                return "Доступные модели:\n" + "\n".join(model_ids)
            return f"⚠️ Ошибка получения моделей ({resp.status_code}): {resp.text}"
    except Exception as e:
        return f"⚠️ Ошибка подключения к Groq: {e}"

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("⚒️ MATIN FORGE CLOUD на связи! Система готова к работе 24/7.")

@dp.message(Command("status"))
async def status_cmd(message: types.Message):
    await message.answer(
        f"⚒️ MATIN FORGE CLOUD В СТРОЮ!\n\n"
        f"• 🌐 Хост: Render (24/7)\n"
        f"• 🧠 Модель: {MODEL_NAME}\n"
        f"• ⚡ Статус: Активен"
    )

@dp.message(Command("models"))
async def models_cmd(message: types.Message):
    """Telegram command that returns the list of available Groq models."""
    reply = await get_models()
    await message.answer(reply)

@dp.message()
async def handle_message(message: types.Message):
    if not message.text:
        return
    status_msg = await message.answer("⏳ Генерирую ответ...")
    reply_text = await call_groq(message.text)
    await status_msg.edit_text(reply_text)

@asynccontextmanager
async def lifespan(app: FastAPI):
    polling_task = None
    if bot:
        # Run polling in background without awaiting its completion
        polling_task = asyncio.create_task(dp.start_polling(bot))
    yield
    if polling_task:
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass