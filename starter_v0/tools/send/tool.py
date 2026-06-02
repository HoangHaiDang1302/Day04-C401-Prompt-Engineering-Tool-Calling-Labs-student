from __future__ import annotations

import os
from typing import Any

import requests

from tools._shared import TIMEOUT, clean_text, err


TELEGRAM_MAX_CHARS = 4096


def _chunks(text: str, size: int = TELEGRAM_MAX_CHARS) -> list[str]:
    return [text[index:index + size] for index in range(0, len(text), size)] or [text]


def send_telegram(text: str = "", confirmed: bool = False) -> dict[str, Any]:
    text = clean_text(text)
    if not confirmed:
        return {
            "tool": "send_telegram",
            "status": "needs_confirmation",
            "message": "Only send after the user explicitly confirms.",
        }
    try:
        if not text:
            raise ValueError("Missing required field: text")
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if not token or not chat_id:
            return {
                "tool": "send_telegram",
                "status": "not_configured",
                "message": "Telegram is not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env, then restart the app.",
                "sent": False,
                "confirmed": True,
            }

        sent_messages = 0
        for chunk in _chunks(text):
            response = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": chunk},
                timeout=TIMEOUT,
            )
            response.raise_for_status()
            sent_messages += 1
        return {"tool": "send_telegram", "status": "sent", "sent": True, "messages_sent": sent_messages}
    except Exception as exc:
        return err("send_telegram", exc)

