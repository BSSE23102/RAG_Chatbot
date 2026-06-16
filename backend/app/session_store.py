from __future__ import annotations

from threading import Lock
from typing import Any


class SessionStore:
    def __init__(self) -> None:
        self._histories: dict[str, Any] = {}
        self._lock = Lock()

    def get_history(self, session_id: str) -> Any:
        with self._lock:
            if session_id not in self._histories:
                from langchain_core.chat_history import InMemoryChatMessageHistory
                self._histories[session_id] = InMemoryChatMessageHistory()
            return self._histories[session_id]

    def snapshot(self, session_id: str) -> list[dict[str, str]]:
        from langchain_core.messages import AIMessage, HumanMessage
        history = self.get_history(session_id)
        snapshot: list[dict[str, str]] = []
        for message in history.messages:
            role = "assistant" if isinstance(message, AIMessage) else "user" if isinstance(message, HumanMessage) else "system"
            snapshot.append({"role": role, "content": message.content})
        return snapshot


session_store = SessionStore()
