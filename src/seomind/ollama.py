from __future__ import annotations

import json
from typing import Any

import httpx

from seomind.config import settings


class OllamaClient:
    async def status(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=2.5) as client:
                response = await client.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags")
            if response.is_error:
                return {"available": False, "models": [], "error": f"HTTP {response.status_code}"}
            models = [str(item.get("name", "")) for item in response.json().get("models", [])]
            return {"available": True, "models": [m for m in models if m]}
        except httpx.HTTPError as exc:
            return {"available": False, "models": [], "error": str(exc)}

    async def explain(self, opportunity: dict[str, Any], language: str, model: str | None) -> dict[str, Any]:
        state = await self.status()
        models = state.get("models", []) if state.get("available") else []
        if not models:
            raise RuntimeError("Ollama is running but no local model is installed.")
        configured = settings.ollama_model
        selected = model or (configured if configured in models else models[0])
        language_name = "Persian (Farsi)" if language == "fa" else "English"
        prompt = f"""
You are SeoMind, a careful SEO analyst. Explain one deterministic Google Search Console finding.
Do not invent traffic, rankings, causes, or facts that are not in the input.
Write in {language_name}.
Return strict JSON only with these keys:
summary: string (max 2 sentences)
why_it_matters: string (max 2 sentences)
actions: array of exactly 3 short actionable strings

Finding:
{json.dumps(opportunity, ensure_ascii=False)}
""".strip()
        payload = {
            "model": selected,
            "stream": False,
            "format": "json",
            "messages": [{"role": "user", "content": prompt}],
        }
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{settings.ollama_base_url.rstrip('/')}/api/chat",
                json=payload,
            )
        if response.is_error:
            raise RuntimeError(f"Ollama request failed: {response.text[:500]}")
        content = response.json().get("message", {}).get("content", "{}")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = {
                "summary": content.strip(),
                "why_it_matters": "",
                "actions": [],
            }
        parsed["model"] = selected
        return parsed


ollama = OllamaClient()
