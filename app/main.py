import os
import logging
from contextlib import asynccontextmanager
from typing import List, Optional

import httpx
from fastapi import FastAPI
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

# ---------------------------------------------------------------------------
# Environment variables
# ---------------------------------------------------------------------------
TOKEN: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
AI_MODEL_ENV: Optional[str] = os.getenv("AI_MODEL")
GROUP_CHAT_ID: Optional[str] = os.getenv("GROUP_CHAT_ID")  # should be a stringified int

# ---------------------------------------------------------------------------
# Global state for model selection
# ---------------------------------------------------------------------------
CANDIDATE_MODELS: List[str] = []  # ordered list of models to try
CURRENT_MODEL_INDEX: int = 0
SELECTED_MODEL: Optional[str] = None

# ---------------------------------------------------------------------------
# Bot / Dispatcher setup
# ---------------------------------------------------------------------------
bot = Bot(token=TOKEN) if TOKEN else None
dp = Dispatcher()

# ---------------------------------------------------------------------------
# Helper: fetch list of models available for the current API key
# ---------------------------------------------------------------------------
async def fetch_available_models() -> List[str]:
    """Return a list of model identifiers that the current GROQ_API_KEY can use.
    The Groq API returns a JSON object with a ``data`` field containing model dicts.
    """
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set in environment")
    url = "https://api.groq.com/openai/v1/models"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        payload = resp.json()
        # Expected format: {"data": [{"id": "model-id", ...}, ...]}
        models = [item.get("id") for item in payload.get("data", []) if isinstance(item, dict) and item.get("id")]
        return models

# ---------------------------------------------------------------------------
# Model selection logic
# ---------------------------------------------------------------------------
async def build_candidate_models() -> List[str]:
    """Construct the ordered fallback list based on environment and available models."""
    available = await fetch_available_models()
    candidates: List[str] = []
    # 1. Explicit AI_MODEL from env (if provided and available)
    if AI_MODEL_ENV:
        candidates.append(AI_MODEL_ENV)
    # 2. Hard‑coded fallbacks
    candidates.extend(["llama-3.1-8b-instant", "llama3-70b-8192"])
    # 3. First text‑oriented model from the API list (simple heuristic)
    for model_id in available:
        if "text" in model_id.lower():
            candidates.append(model_id)
            break
    # Remove duplicates while preserving order
    seen = set()
    ordered: List[str] = []
    for m in candidates:
        if m not in seen:
            seen.add(m)
            ordered.append(m)
    # Finally, keep only those that are actually present in the API list
    filtered = [m for m in ordered if m in available]
    return filtered

async def initialise_model_selection() -> None:
    global CANDIDATE_MODELS, CURRENT_MODEL_INDEX, SELECTED_MODEL
    CANDIDATE_MODELS = await build_candidate_models()
    if not CANDIDATE_MODELS:
        raise RuntimeError("No usable Groq models were found for the provided API key.")
    CURRENT_MODEL_INDEX = 0
    SELECTED_MODEL = CANDIDATE_MODELS[0]
    logging.info(f"Model selection initialised. Candidates: {CANDIDATE_MODELS}")

# ---------------------------------------------------------------------------
# Core request helper with automatic fallback on 404
# ---------------------------------------------------------------------------
async def ask_groq(prompt: str) -> str:
    """Send *prompt* to Groq using the current selected model.
    If the request fails with a 404 indicating the model is unavailable, the function
    transparently switches to the next candidate model and retries.
    """
    if not GROQ_API_KEY:
        return "⚠️ GROQ_API_KEY не найден в переменных окружения!"
    if not SELECTED_MODEL:
        return "⚠️ Не удалось определить рабочую модель Groq."

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload_base = {
        "messages": [
            {
                "role": "system",
                "content": "Ты MATIN FORGE CLOUD — 24/7 облачный технический AI‑партнёр. Отвечай кратко, чётко, технически грамотно и без лишней воды."
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        while True:
            payload = payload_base.copy()
            payload["model"] = SELECTED_MODEL
            try:
                resp = await client.post(url, headers=headers, json=payload)
            except Exception as exc:
                return f"⚠️ Ошибка соединения с Groq: {exc}"

            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
            # Handle model‑not‑found – Groq returns 404 with an error code "model_not_found"
            if resp.status_code == 404 and "model_not_found" in resp.text.lower():
                logging.warning(f"Model {SELECTED_MODEL} недоступна (404). Переходим к следующей модели.")
                # Move to next candidate
                global CURRENT_MODEL_INDEX, SELECTED_MODEL
                CURRENT_MODEL_INDEX += 1
                if CURRENT_MODEL_INDEX >= len(CANDIDATE_MODELS):
                    return "⚠️ Все модели из списка недоступны. Попробуйте позже."
                SELECTED_MODEL = CANDIDATE_MODELS[CURRENT_MODEL_INDEX]
                continue
            # Any other error – surface it
            return f"⚠️ Ошибка Groq ({resp.status_code}): {resp.text}"

# ---------------------------------------------------------------------------
# Self‑test routine executed on startup
# ---------------------------------------------------------------------------
async def run_self_test() -> bool:
    """Send a simple prompt to verify the selected model works.
    Returns ``True`` if the test succeeded, ``False`` otherwise.
    """
    test_prompt = "Тест связи: напиши OK"
    response = await ask_groq(test_prompt)
    if response.startswith("⚠️"):
        return False
    return bool(response.strip())

# ---------------------------------------------------------------------------
# FastAPI application with lifespan for initialisation
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialise model list
    await initialise_model_selection()
    # Run self‑test and report
    test_passed = await run_self_test()
    report = (
        f"✅ Выбранная модель: {SELECTED_MODEL}\n"
        f"🧪 Тест соединения: {'Успешно' if test_passed else 'Не удалось'}"
    )
    if bot and GROUP_CHAT_ID:
        try:
            await bot.send_message(chat_id=int(GROUP_CHAT_ID), text=report)
        except Exception as exc:
            logging.error(f"Не удалось отправить отчёт в группу: {exc}")
    else:
        logging.info("Bot token или GROUP_CHAT_ID не заданы – отчёт не отправлен.")
    yield
    # Graceful shutdown
    if bot:
        await bot.session.close()

app = FastAPI(lifespan=lifespan)

# ---------------------------------------------------------------------------
# Bot command handlers
# ---------------------------------------------------------------------------
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer("⚒️ MATIN FORGE CLOUD на связи! Система готова к работе 24/7.")

@dp.message(Command("status"))
async def status_handler(message: types.Message):
    model_info = SELECTED_MODEL or "не определена"
    await message.answer(
        f"⚒️ MATIN FORGE CLOUD (ОБЛАЧНЫЙ КУЗНЕЦ) В СТРОЮ!\n\n• 🌐 Хост: Render (Cloud 24/7)\n• 🧠 Модель: {model_info}\n• ⚡️ Статус: Активен"
    )

@dp.message(F.text)
async def text_handler(message: types.Message):
    if not bot:
        return
    is_private = message.chat.type == "private"
    bot_info = await bot.get_me()
    is_mentioned = bot_info.username and f"@{bot_info.username}" in (message.text or "")
    is_reply = message.reply_to_message and message.reply_to_message.from_user.id == bot_info.id

    if is_private or is_mentioned or is_reply:
        prompt = message.text.replace(f"@{bot_info.username}", "").strip() if is_mentioned else message.text.strip()
        if not prompt:
            return
        answer = await ask_groq(prompt)
        await message.answer(answer)

# Register dispatcher with FastAPI
@app.on_event("startup")
async def on_startup():
    # Start polling in background
    if bot:
        await dp.start_polling(bot)
