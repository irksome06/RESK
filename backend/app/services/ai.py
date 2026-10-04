from __future__ import annotations

import httpx
from app.core.config import settings


async def explain(payload: dict) -> dict:
    if not settings.gemini_api_key:
        return {
            "source": "local-fallback",
            "summary": "Shift flexible production into lower-tariff windows, flatten the evening peak, and investigate the flagged load deviation before it becomes a persistent efficiency loss.",
            "actions": [
                "Move Batch B and Batch D away from 18:00–22:00 whenever production constraints allow.",
                "Review the latest anomaly against machine state and operator logs.",
                "Use the maintenance window with the lowest production conflict for the next service cycle.",
            ],
        }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
    prompt = (
        "You are an industrial energy optimization copilot. Explain the following factory optimization result in plain language. "
        "Return JSON-like content with a concise summary and exactly three actionable recommendations. Do not invent sensor values.\n\n"
        + str(payload)
    )
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
        response.raise_for_status()
        data = response.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return {"source": "gemini", "summary": text, "actions": []}
