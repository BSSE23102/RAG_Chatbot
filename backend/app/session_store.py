from __future__ import annotations

from threading import Lock

from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import AIMessage, HumanMessage


class SessionStore:
    def __init__(self) -> None:
        self._histories: dict[str, InMemoryChatMessageHistory] = {}
        self._lock = Lock()

    def get_history(self, session_id: str) -> InMemoryChatMessageHistory:
        with self._lock:
            if session_id not in self._histories:
                self._histories[session_id] = InMemoryChatMessageHistory()
            return self._histories[session_id]

    def snapshot(self, session_id: str) -> list[dict[str, str]]:
        history = self.get_history(session_id)
        snapshot: list[dict[str, str]] = []
        for message in history.messages:
            role = "assistant" if isinstance(message, AIMessage) else "user" if isinstance(message, HumanMessage) else "system"
            snapshot.append({"role": role, "content": message.content})
        return snapshot


session_store = SessionStore()
