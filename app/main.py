import os
import asyncio
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = "llama-3.1-8b-instant"

bot = Bot(token=TOKEN) if TOKEN else None
dp = Dispatcher()

async def call_groq(prompt: str) -> str:
    if not GROQ_KEY:
        return "⚠️ GROQ_API_KEY не задан в переменных Render!"
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "Ты — MATIN FORGE CLOUD, облачный ассистент и кузнец инструментов. Отвечай точно и по делу."},
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
        return f"⚠️ Сетевая ошибка Groq: {e}"

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
        print(">>> ЗАПУСК TELEGRAM POLLING...", flush=True)
        polling_task = asyncio.create_task(dp.start_polling(bot))
    yield
    if bot:
        await bot.session.close()
        if polling_task:
            polling_task.cancel()
            try:
                await polling_task
            except asyncio.CancelledError:
                pass

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"status": "ok", "service": "matin_forge_cloud"}
