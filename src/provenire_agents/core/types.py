"""Базови типове за многоагентната система.

Определя протокола, по който агентите обменят информация: съобщения,
резултати от анализ и критични бележки.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class Severity(str, Enum):
    """Тежест на критична бележка."""
    INFO = "info"
    MINOR = "minor"
    MAJOR = "major"
    BLOCKER = "blocker"


class AgentRole(str, Enum):
    """Роли на агентите в системата."""
    ORCHESTRATOR = "Оркестратор"
    RESEARCHER = "Учен"
    DATA = "Данни"
    ANALYST = "Оценка"
    RISK = "Риск"
    CRITIC = "Критик"
    COMPLIANCE = "Съответствие"
    ADVISOR = "Препоръка"


@dataclass
class Message:
    """Съобщение в дневника на консултацията."""
    sender: AgentRole
    content: str
    round_no: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)

    def short(self) -> str:
        return f"[{self.timestamp:%H:%M:%S}] {self.sender.value}: {self.content}"


@dataclass
class Critique:
    """Единично възражение от агента Критик."""
    severity: Severity
    target: AgentRole
    issue: str
    suggestion: str

    @property
    def blocking(self) -> bool:
        return self.severity in (Severity.MAJOR, Severity.BLOCKER)

    def __str__(self) -> str:
        return f"[{self.severity.value.upper()}] {self.target.value}: {self.issue} → {self.suggestion}"


@dataclass
class Finding:
    """Резултат от работата на един агент."""
    agent: AgentRole
    summary: str
    payload: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    sources: List[str] = field(default_factory=list)
    revised: bool = False        # дали е преработен след критика

    def __str__(self) -> str:
        return f"{self.agent.value}: {self.summary}"


@dataclass
class ConsultationResult:
    """Краен резултат от целия консултативен цикъл."""
    question: str
    findings: List[Finding] = field(default_factory=list)
    critiques: List[Critique] = field(default_factory=list)
    transcript: List[Message] = field(default_factory=list)
    recommendation: str = ""
    rounds: int = 0

    def finding_by(self, role: AgentRole) -> Optional[Finding]:
        for f in self.findings:
            if f.agent == role:
                return f
        return None

    @property
    def unresolved(self) -> List[Critique]:
        return [c for c in self.critiques if c.blocking]
