"""Оркестратор на многоагентната консултация.

Управлява цикъла: специалистите изготвят анализ → Критикът оспорва →
специалистите преработват → повтаря се до изчерпване на кръговете или
до липса на съществени възражения.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from .agent_base import Agent, LLMClient, OfflineLLM
from .aisim import DEFAULT_ALPHA, DEFAULT_PROFILE, WEIGHTS, as_records
from .types import AgentRole, ConsultationResult, Critique, Finding, Message


class Orchestrator:
    """Координира работата на всички агенти."""

    def __init__(self, llm: Optional[LLMClient] = None, max_rounds: int = 3):
        from ..agents.researcher import ResearcherAgent
        from ..agents.analysts import AnalystAgent, DataAgent, RiskAgent
        from ..agents.control import AdvisorAgent, ComplianceAgent, CriticAgent

        self.llm = llm or OfflineLLM()
        self.max_rounds = max_rounds

        self.researcher = ResearcherAgent(self.llm)
        self.data = DataAgent(self.llm)
        self.analyst = AnalystAgent(self.llm)
        self.risk = RiskAgent(self.llm)
        self.critic = CriticAgent(self.llm)
        self.compliance = ComplianceAgent(self.llm)
        self.advisor = AdvisorAgent(self.llm)

        # редът на изказване на специалистите
        self.specialists: List[Agent] = [
            self.researcher, self.data, self.analyst, self.risk,
        ]

    @property
    def roster(self) -> List[Agent]:
        """Пълният състав на екипа."""
        return self.specialists + [self.critic, self.compliance, self.advisor]

    def run(self,
            question: str = "Оцени и класирай доставчиците",
            suppliers: Optional[List[Dict]] = None,
            profile: str = DEFAULT_PROFILE,
            alpha: float = DEFAULT_ALPHA,
            llm_mode: str = "offline",
            on_event: Optional[Callable[[Message], None]] = None,
            ) -> ConsultationResult:
        """Провежда пълната консултация и връща резултата."""

        suppliers = suppliers if suppliers is not None else as_records()
        weights = WEIGHTS.get(profile, WEIGHTS[DEFAULT_PROFILE])

        result = ConsultationResult(question=question)
        ctx: Dict[str, Any] = {
            "question": question,
            "suppliers": suppliers,
            "weights": weights,
            "alpha": alpha,
            "profile": profile,
            "llm_mode": llm_mode,
            "round": 1,
        }

        def emit(msg: Message) -> None:
            result.transcript.append(msg)
            if on_event:
                on_event(msg)

        emit(Message(sender=AgentRole.ORCHESTRATOR,
                     content=(f'Начало на консултация: {question}. '
                              f'Профил: {profile}; alpha = {alpha:.2f}; режим: {llm_mode}.'),
                     round_no=0))

        findings: List[Finding] = []
        all_critiques: List[Critique] = []

        for rnd in range(1, self.max_rounds + 1):
            ctx["round"] = rnd
            emit(Message(sender=AgentRole.ORCHESTRATOR,
                         content=f"--- Кръг {rnd} ---", round_no=rnd))

            # 1. специалистите работят (или преработват)
            if rnd == 1:
                findings = []
                for agent in self.specialists:
                    f = agent.work(ctx)
                    findings.append(f)
                    emit(Message(sender=agent.role, content=f.summary, round_no=rnd))
            else:
                revised: List[Finding] = []
                for agent, f in zip(self.specialists, findings):
                    targeted = [str(c) for c in all_critiques
                                if c.target == agent.role and c.blocking]
                    if targeted:
                        f = agent.revise(f, targeted, ctx)
                        emit(Message(sender=agent.role,
                                     content=f"Преработено по {len(targeted)} възражения.",
                                     round_no=rnd))
                    revised.append(f)
                findings = revised

            # 1б. проверка за съответствие преди критиката
            compliance = self.compliance.work({**ctx, "findings": findings})
            findings = [f for f in findings if f.agent != AgentRole.COMPLIANCE]
            findings.append(compliance)
            emit(Message(sender=AgentRole.COMPLIANCE, content=compliance.summary,
                         round_no=rnd))

            ctx["findings"] = findings

            # 2. критикът оспорва
            crit_finding = self.critic.work(ctx)
            round_critiques: List[Critique] = crit_finding.payload["critiques"]
            all_critiques = round_critiques
            ctx["critiques"] = round_critiques
            emit(Message(sender=AgentRole.CRITIC, content=crit_finding.summary, round_no=rnd))
            for c in round_critiques:
                emit(Message(sender=AgentRole.CRITIC, content=str(c), round_no=rnd))

            result.rounds = rnd

            # 3. спираме, ако няма съществени възражения
            if not any(c.blocking for c in round_critiques):
                emit(Message(sender=AgentRole.ORCHESTRATOR,
                             content="Няма съществени възражения — преминаване към синтез.",
                             round_no=rnd))
                break

        # 4. окончателна препоръка (след преминато съответствие)
        ctx["findings"] = findings
        advice = self.advisor.work(ctx)
        findings.append(advice)
        emit(Message(sender=AgentRole.ADVISOR, content=advice.summary, round_no=result.rounds))

        result.findings = findings
        result.critiques = all_critiques
        result.recommendation = advice.payload.get("recommendation", "")

        emit(Message(sender=AgentRole.ORCHESTRATOR,
                     content=f"Консултацията приключи след {result.rounds} кръга.",
                     round_no=result.rounds))
        return result
