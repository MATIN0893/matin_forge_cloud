import os
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = Bot(token=TOKEN) if TOKEN else None
dp = Dispatcher()

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

@asynccontextmanager
async def lifespan(app: FastAPI):
    if bot:
        print(">>> ЗАПУСК TELEGRAM POLLING...", flush=True)
        polling_task = asyncio.create_task(dp.start_polling(bot))
    else:
        print(">>> ОШИБКА: TELEGRAM_BOT_TOKEN не найден!", flush=True)
        polling_task = None
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
    return {"status": "ok", "agent": "matin_forge_cloud"}
