import os
import logging
from typing import List, Optional

import httpx
from fastapi import FastAPI

# ---------------------------------------------------------------------------
# Logger configuration
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------------------------------
# Environment variables
# ---------------------------------------------------------------------------
TOKEN: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
GROQ_ENDPOINT: str = os.getenv(
    "GROQ_ENDPOINT", "https://api.groq.com/openai/v1/chat/completions"
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MODELS: List[str] = [
    "llama-3.1-8b-instant",
    "llama3-70b-8192",
    "llama3-8b-8192",
]

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI()

@app.get("/health")
async def health_check() -> dict:
    """Simple health endpoint used for monitoring."""
    return {"status": "ok"}

# ---------------------------------------------------------------------------
# Groq interaction helper
# ---------------------------------------------------------------------------
async def ask_groq(prompt: str) -> str:
    """Send *prompt* to Groq using a fallback list of models.

    The function iterates over :data:`MODELS`. For each model it performs a
    POST request to the Groq chat‑completion endpoint. If a model returns a
    ``200`` response, the assistant's reply is extracted and returned.
    When a model is unavailable (e.g., ``404`` or any request error), a log
    entry ``"Модель {model} недоступна, пробуем следующую..."`` is emitted and
    the next model is tried. If none of the models succeed, a user‑friendly
    error message is returned.
    """
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set in environment")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    for model in MODELS:
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a helpful AI assistant that answers user "
                        "queries concisely and accurately."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 1024,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(GROQ_ENDPOINT, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            logger.info("Model %s unavailable (%s), trying next model...", model, exc)
            logger.info("Модель %s недоступна, пробуем следующую...", model)
            continue

        if response.status_code == 200:
            data = response.json()
            choices = data.get("choices", [])
            if choices:
                return choices[0]["message"]["content"].strip()
            logger.warning("Model %s returned 200 but no choices were found.", model)
            # Fall through to try next model
        else:
            logger.info(
                "Model %s returned status %s, trying next model...",
                model,
                response.status_code,
            )
            logger.info("Модель %s недоступна, пробуем следующую...", model)
            # Continue to next model

    return "Все модели недоступны. Пожалуйста, попробуйте позже."
