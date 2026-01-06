from __future__ import annotations

import hashlib
import json
import os
from typing import Any

import requests


class GroqText:
    def __init__(self, api_key: str, model: str, max_calls: int) -> None:
        self._enabled = bool(api_key)
        self._api_key = api_key
        self._model = model
        self._remaining = max_calls
        self._cache: dict[str, str] = {}

        # Groq provides an OpenAI-compatible API surface.
        self._base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

    @property
    def enabled(self) -> bool:
        return self._enabled and self._remaining > 0

    def _key(self, payload: Any) -> str:
        b = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(b).hexdigest()

    def complete(self, system: str, user: str, temperature: float = 0.6, max_tokens: int = 600) -> str:
        if not self.enabled:
            raise RuntimeError("GroqText is disabled or exhausted")

        payload = {
            "system": system,
            "user": user,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "model": self._model,
        }
        k = self._key(payload)
        if k in self._cache:
            return self._cache[k]

        self._remaining -= 1

        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        resp = requests.post(url, headers=headers, json=body, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content")
        text = (text or "").strip()
        self._cache[k] = text
        return text


def build_groq_from_env() -> GroqText:
    api_key = os.getenv("GROQ_API_KEY", "")
    model = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
    max_calls = int(os.getenv("GROQ_MAX_CALLS", "40"))
    return GroqText(api_key=api_key, model=model, max_calls=max_calls)
