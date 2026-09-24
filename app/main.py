import os
import asyncio
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "https://matin-forge-cloud.onrender.com")

bot = Bot(token=TOKEN) if TOKEN else None
dp = Dispatcher()

async def ask_groq(prompt: str) -> str:
    if not GROQ_KEY:
        return "⚠️ GROQ_API_KEY не найден в переменных Render!"
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "system",
                "content": "Ты MATIN FORGE CLOUD — 24/7 облачный технический AI-партнёр. Отвечай кратко, чётко, технически грамотно и без лишней воды."
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                return f"⚠️ Ошибка Groq ({resp.status_code}): {resp.text}"
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"⚠️ Ошибка соединения с Groq: {str(e)}"

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer("⚒️ MATIN FORGE CLOUD на связи! Система готова к работе 24/7.")

@dp.message(Command("status"))
async def status_handler(message: types.Message):
    await message.answer("⚒️ MATIN FORGE CLOUD (ОБЛАЧНЫЙ КУЗНЕЦ) В СТРОЮ!\n\n• 🌐 Хост: Render (Cloud 24/7)\n• 🧠 Модель: Groq Llama 3.3\n• ⚡️ Статус: Активен")

@dp.message(F.text)
async def text_handler(message: types.Message):
    is_private = message.chat.type == "private"
    bot_info = await bot.get_me()
    is_mentioned = bot_info.username and f"@{bot_info.username}" in (message.text or "")
    is_reply = message.reply_to_message and message.reply_to_message.from_user.id == bot_info.id

    if is_private or is_mentioned or is_reply:
        prompt = message.text.replace(f"@{bot_info.username}", "").strip() if is_mentioned else message.text
        if not prompt:
            return
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
        reply = await ask_groq(prompt)
        for i in range(0, len(reply), 4000):
            await message.answer(reply[i:i+4000])

async def keep_alive():
    await asyncio.sleep(60)
    while True:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.get(RENDER_URL)
        except Exception:
            pass
        await asyncio.sleep(600)

@asynccontextmanager
async def lifespan(app: FastAPI):
    if bot:
        print(">>> ЗАПУСК TELEGRAM POLLING...", flush=True)
        asyncio.create_task(dp.start_polling(bot))
        asyncio.create_task(keep_alive())
    yield
    if bot:
        await bot.session.close()

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"status": "ok", "agent": "matin_forge_cloud"}
