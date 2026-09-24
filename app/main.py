import os
import asyncio
from contextlib import asynccontextmanager
from typing import Optional

import httpx
from fastapi import FastAPI
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

from app.planner import ask_groq

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = Bot(token=TOKEN) if TOKEN else None
dp = Dispatcher()

# ---------- Bot command handlers ----------
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer("⚒️ MATIN FORGE CLOUD на связи! Система готова к работе 24/7.")

@dp.message(Command("status"))
async def status_handler(message: types.Message):
    await message.answer(
        "⚒️ MATIN FORGE CLOUD (ОБЛАЧНЫЙ КУЗНЕЦ) В СТРОЮ!\n\n"
        "• 🌐 Хост: Render (Cloud 24/7)\n"
        "• 🧠 Модель: Groq Llama 3.3\n"
        "• ⚡️ Статус: Активен"
    )

# ---------- Generic message handler (AI assistant) ----------
@dp.message()
async def ai_assistant_handler(message: types.Message):
    # Determine whether the bot should respond
    respond: bool = False
    if message.chat.type == "private":
        respond = True
    else:
        # Group chat – respond if bot is mentioned or replied to
        bot_info = await bot.get_me()
        bot_username = bot_info.username
        # Check mentions in entities
        if message.entities:
            for entity in message.entities:
                if entity.type == "mention":
                    mention = message.text[entity.offset:entity.offset + entity.length]
                    if mention.lstrip("@") == bot_username:
                        respond = True
                        break
        # Check reply to bot
        if not respond and message.reply_to_message and message.reply_to_message.from_user:
            if message.reply_to_message.from_user.id == bot_info.id:
                respond = True
        # Fallback: plain text contains @username
        if not respond and f"@{bot_username}" in message.text:
            respond = True
    if not respond:
        return

    # Call Groq LLM for a response
    try:
        answer = await ask_groq(message.text)
    except Exception as e:
        answer = f"Ошибка при обращении к модели: {e}"
    await message.reply(answer, allow_sending_without_reply=True)

# ---------- Self‑ping coroutine to keep Render instance alive ----------
SELF_PING_URL = "https://matin-forge-cloud.onrender.com"
PING_INTERVAL = 600  # seconds (10 minutes)

async def self_ping_loop() -> None:
    while True:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.get(SELF_PING_URL)
        except Exception:
            # Silently ignore any network errors – the goal is just to keep the instance alive
            pass
        await asyncio.sleep(PING_INTERVAL)

# ---------- Application lifespan ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start Telegram polling if token is provided
    polling_task: Optional[asyncio.Task] = None
    if bot:
        print(">>> ЗАПУСК TELEGRAM POLLING...", flush=True)
        polling_task = asyncio.create_task(dp.start_polling(bot))
    else:
        print(">>> ОШИБКА: TELEGRAM_BOT_TOKEN не найден!", flush=True)

    # Start self‑ping background task
    ping_task = asyncio.create_task(self_ping_loop())

    yield

    # Graceful shutdown
    if bot:
        await bot.session.close()
    if polling_task:
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
    ping_task.cancel()
    try:
        await ping_task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"status": "ok", "agent": "matin_forge_cloud"}
