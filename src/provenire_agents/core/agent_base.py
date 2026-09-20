"""Базов агент и абстракция на езиковия модел.

Езиковият модел е зад интерфейс, за да може приложението да работи
с локален модел (on-premise) или без модел изобщо (детерминистичен режим).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .types import AgentRole, Finding, Message


class LLMClient(ABC):
    """Интерфейс към езиков модел."""

    @abstractmethod
    def complete(self, system: str, prompt: str) -> str:
        """Връща отговор на модела."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Име на модела, за показване в интерфейса."""


class OfflineLLM(LLMClient):
    """Детерминистичен заместител, когато няма наличен модел.

    Позволява цялата агентна логика да се изпълнява и тества без
    външна зависимост — агентите работят с правила вместо с модел.
    """

    @property
    def name(self) -> str:
        return "Офлайн режим (без езиков модел)"

    def complete(self, system: str, prompt: str) -> str:
        return ""


class LocalLLM(LLMClient):
    """Клиент към локален модел през Ollama (on-premise)."""

    def __init__(self, model: str = "qwen2.5:1.5b", host: str = "http://localhost:11434"):
        self.model = model
        self.host = host

    @property
    def name(self) -> str:
        return f"Локален модел: {self.model}"

    def complete(self, system: str, prompt: str) -> str:
        import json
        import urllib.request

        body = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": False,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{self.host}/api/generate", data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read()).get("response", "")


class Agent(ABC):
    """Базов клас за всички агенти."""

    role: AgentRole
    description: str = ""

    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or OfflineLLM()
        self._log: List[Message] = []

    def say(self, content: str, round_no: int = 0, **data: Any) -> Message:
        """Записва изказване в дневника."""
        msg = Message(sender=self.role, content=content, round_no=round_no, data=data)
        self._log.append(msg)
        return msg

    @abstractmethod
    def work(self, context: Dict[str, Any]) -> Finding:
        """Изпълнява задачата на агента и връща резултат."""

    def revise(self, finding: Finding, critiques: List[str],
               context: Dict[str, Any]) -> Finding:
        """Преработва резултата след критика.

        Базовата реализация отбелязва преработката; специализираните
        агенти я предефинират със собствена логика.
        """
        if not critiques:
            return finding
        finding.revised = True
        finding.summary += " (преработено след критика)"
        finding.payload.setdefault("addressed_critiques", []).extend(critiques)
        return finding

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} role={self.role.value}>"
