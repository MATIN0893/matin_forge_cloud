import os
import json
import httpx
from typing import Any

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_ENDPOINT = os.getenv("GROQ_ENDPOINT", "https://api.groq.com/openai/v1/chat/completions")
MODEL = os.getenv("GROQ_MODEL", "mixtral-8x7b-32768")

async def generate_plan(prompt: str) -> str:
    """Generate a step‑by‑step plan using the Groq LLM.

    Args:
        prompt: The user supplied description of the goal.
    Returns:
        A textual plan.
    """
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set in environment")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are a planner that creates concise step‑by‑step instructions for a given task."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 1024,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(GROQ_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("No choices returned from Groq API")
        return choices[0]["message"]["content"].strip()

# ---------- General chat completion helper (AI assistant) ----------
async def ask_groq(prompt: str) -> str:
    """Send a user prompt to the configured Groq model and return the assistant's reply.

    This uses the same endpoint as ``generate_plan`` but with a more generic system prompt.
    """
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set in environment")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful AI assistant that answers user queries concisely and accurately."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 1024,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(GROQ_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("No choices returned from Groq API")
        return choices[0]["message"]["content"].strip()
