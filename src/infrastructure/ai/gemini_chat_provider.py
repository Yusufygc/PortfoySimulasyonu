# -*- coding: utf-8 -*-
"""Google Gemini SDK üzerinden çalışan sohbet sağlayıcısı.

`IAIChatProvider` portunu uygular. SDK ve API anahtarı bu katmanda kalır;
UI/application SDK detaylarını bilmez. Hata metinleri sadedir.
"""

from __future__ import annotations

from typing import Sequence, Tuple

from src.domain.ports.services.i_ai_chat_provider import IAIChatProvider

_MODEL_NAME = "gemini-3-flash-preview"

_SAFETY_CATEGORIES = (
    "HARM_CATEGORY_HATE_SPEECH",
    "HARM_CATEGORY_HARASSMENT",
    "HARM_CATEGORY_SEXUALLY_EXPLICIT",
    "HARM_CATEGORY_DANGEROUS_CONTENT",
)


def _load_gemini_sdk():
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError(
            "google-genai kütüphanesi eksik. Lütfen 'pip install google-genai' çalıştırın."
        ) from exc
    return genai, types


class GeminiChatProvider(IAIChatProvider):
    def __init__(self, api_key: str | None) -> None:
        self._api_key = api_key

    def generate(self, system_prompt: str, turns: Sequence[Tuple[str, str]]) -> str:
        if not self._api_key:
            raise RuntimeError("Yapay zeka anahtarı bulunamadı. Lütfen GEMINI_API_KEY tanımlayın.")
        if not turns:
            raise RuntimeError("Gemini isteği için mesaj bulunamadı.")

        genai, types = _load_gemini_sdk()
        try:
            client = genai.Client(api_key=self._api_key)

            safety_settings = [
                types.SafetySetting(
                    category=getattr(types.HarmCategory, category),
                    threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                )
                for category in _SAFETY_CATEGORIES
            ]

            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                safety_settings=safety_settings,
            )

            history = [
                types.Content(role=role, parts=[types.Part.from_text(text=text)])
                for role, text in turns[:-1]
            ]

            chat = client.chats.create(
                model=_MODEL_NAME,
                config=config,
                history=history,
            )

            last_text = turns[-1][1]
            response = chat.send_message(last_text)
            return response.text
        except Exception as exc:
            raise RuntimeError(f"Yapay zeka yanıtı alınamadı: {exc}") from exc
