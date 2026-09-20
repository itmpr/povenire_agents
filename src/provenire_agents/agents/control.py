"""Агенти за контрол и синтез: Критик, Съответствие, Препоръка."""
from __future__ import annotations

import re
from typing import Any, Dict, List

from ..core.agent_base import Agent
from ..core.aisim import DIM_NAMES, score_gaps
from ..core.types import AgentRole, Critique, Finding, Severity

# Образци за чувствителна информация, която не бива да напуска средата
SENSITIVE_PATTERNS = [
    (r"cost\s*breakdown|разбивка\s*на\s*себестойност", "структура на себестойността"),
    (r"\bмарж\b|\bmargin\b", "информация за марж"),
    (r"чертеж|drawing|CAD\b", "техническа документация"),
    (r"оферт[аи]|quotation", "оферта на доставчик"),
    (r"\bIBAN\b|\bБУЛСТАТ\b|\bЕИК\b", "идентификационни данни"),
]


class CriticAgent(Agent):
    """Оспорва анализа на останалите агенти и връща възражения."""

    role = AgentRole.CRITIC
    description = ("Проверява допусканията, пропуските в данните, обосноваността на "
                   "препоръките и коректността на цитатите.")

    def _check_data(self, f: Finding) -> List[Critique]:
        out = []
        q = f.payload.get("data_quality", 100)
        issues = f.payload.get("issues", [])
        if q < 90:
            out.append(Critique(
                severity=Severity.MAJOR if q < 75 else Severity.MINOR,
                target=AgentRole.DATA,
                issue=f"Качеството на данните е {q}% ({len(issues)} установени проблема).",
                suggestion="Допълване на липсващите стойности преди да се разчита на оценката.",
            ))
        return out

    def _check_analysis(self, f: Finding, ctx: Dict[str, Any]) -> List[Critique]:
        out = []
        ranked = f.payload.get("ranked", [])
        if not ranked:
            return out

        # разчитане на цена въпреки слаби качество и риск
        drop = f.payload.get("biggest_drop") or {}
        if drop.get("shift", 0) <= -3:
            out.append(Critique(
                severity=Severity.MAJOR,
                target=AgentRole.ANALYST,
                issue=(f"Доставчик {drop['code']} е №{drop['price_rank']} по цена, но "
                       f"№{drop['fais_rank']} по интегрирана оценка."),
                suggestion="Ценовото предимство не бива да се представя самостоятелно — "
                           "да се посочат изрично компенсиращите го слабости.",
            ))

        # твърде близки резултати на върха
        if len(ranked) >= 2:
            gap = ranked[0]["FAIS"] - ranked[1]["FAIS"]
            if gap < 1.0:
                out.append(Critique(
                    severity=Severity.MINOR,
                    target=AgentRole.ANALYST,
                    issue=(f"Разликата между първите двама ({ranked[0]['code']} и "
                           f"{ranked[1]['code']}) е едва {gap:.1f} точки."),
                    suggestion="Да се извърши анализ на чувствителността преди номинация.",
                ))

        # доставчик с червено предупреждение сред водещите
        for r in ranked[:3]:
            if r["warning"] == "Червено":
                out.append(Critique(
                    severity=Severity.BLOCKER,
                    target=AgentRole.ANALYST,
                    issue=f"{r['code']} е сред първите три, но с червено предупреждение "
                          f"({r['risk_prob']}% вероятност за прекъсване).",
                    suggestion="Номинацията да се обвърже с план за втори източник.",
                ))
        return out

    def _check_risk(self, f: Finding) -> List[Critique]:
        out = []
        hidden = f.payload.get("hidden_risk", [])
        for h in hidden:
            out.append(Critique(
                severity=Severity.MAJOR,
                target=AgentRole.RISK,
                issue=(f"{h['code']} има добра текуща оценка ({h['css']}), но прогнозата се "
                       f"влошава с {h['trend']} точки."),
                suggestion="Скритото влошаване да бъде изведено на преден план в препоръката.",
            ))
        return out

    def _check_research(self, f: Finding) -> List[Critique]:
        """Проверява цитатите — основният риск при научния агент."""
        out = []
        papers = f.payload.get("papers", [])
        text = f.payload.get("section_text", "")

        # всяко цитиране в текста трябва да отговаря на реален източник
        years_in_corpus = {str(p["year"]) for p in papers}
        cited_years = set(re.findall(r"\b((?:19|20)\d{2})\b", text))
        unknown = cited_years - years_in_corpus
        if unknown:
            out.append(Critique(
                severity=Severity.BLOCKER,
                target=AgentRole.RESEARCHER,
                issue=f"В текста се срещат години без съответстващ източник: {sorted(unknown)}.",
                suggestion="Всяко твърдение да бъде обвързано с проверен източник.",
            ))

        if len(papers) < 8:
            out.append(Critique(
                severity=Severity.MINOR,
                target=AgentRole.RESEARCHER,
                issue=f"Обзорът обхваща само {len(papers)} публикации.",
                suggestion="Разширяване на обхвата за по-пълно покритие на областта.",
            ))

        notes = f.payload.get("methodology_notes", [])
        for n in notes:
            out.append(Critique(
                severity=Severity.MAJOR,
                target=AgentRole.ANALYST,
                issue=f"Методологична бележка от научния надзор: {n}",
                suggestion="Да се отрази в ограниченията на изследването или да се коригира.",
            ))
        return out

    def _check_compliance(self, f: Finding) -> List[Critique]:
        """Констатациите на агента за съответствие са с най-висок приоритет."""
        out = []
        if f.payload.get("verdict") == "Блокирано":
            types = {t for e in f.payload.get("exposures", []) for t in e["types"]}
            out.append(Critique(
                severity=Severity.BLOCKER,
                target=AgentRole.COMPLIANCE,
                issue=("Чувствителна информация (" + ", ".join(sorted(types)) +
                       ") би напуснала средата при избрания режим."),
                suggestion="Преминаване към локален режим или анонимизиране преди обработка.",
            ))
        return out

    def work(self, context: Dict[str, Any]) -> Finding:
        findings: List[Finding] = context.get("findings", [])
        critiques: List[Critique] = []

        for f in findings:
            if f.agent == AgentRole.DATA:
                critiques += self._check_data(f)
            elif f.agent == AgentRole.ANALYST:
                critiques += self._check_analysis(f, context)
            elif f.agent == AgentRole.RISK:
                critiques += self._check_risk(f)
            elif f.agent == AgentRole.RESEARCHER:
                critiques += self._check_research(f)
            elif f.agent == AgentRole.COMPLIANCE:
                critiques += self._check_compliance(f)

        # Вече признатите възражения не се повдигат отново със същата тежест:
        # те са отразени от съответния агент и остават като документирана бележка.
        acknowledged: set[str] = set()
        for f in findings:
            for a in f.payload.get("addressed_critiques", []) or []:
                acknowledged.add(a)

        if acknowledged:
            adjusted: List[Critique] = []
            for c in critiques:
                if str(c) in acknowledged:
                    adjusted.append(Critique(
                        severity=Severity.INFO, target=c.target,
                        issue=c.issue + " (признато и отразено)",
                        suggestion=c.suggestion,
                    ))
                else:
                    adjusted.append(c)
            critiques = adjusted

        blocking = [c for c in critiques if c.blocking]
        self.say(f"Повдигнати {len(critiques)} възражения, от които {len(blocking)} съществени.",
                 context.get("round", 0))
        return Finding(
            agent=self.role,
            summary=f"{len(critiques)} възражения ({len(blocking)} съществени).",
            payload={"critiques": critiques},
            confidence=1.0,
        )


class ComplianceAgent(Agent):
    """Проверява за изтичане на поверителна информация и регулаторно съответствие."""

    role = AgentRole.COMPLIANCE
    description = "Проверява поверителността на данните преди напускане на средата."

    def scan(self, text: str) -> List[str]:
        """Открива чувствителни елементи в текст."""
        hits = []
        for pattern, label in SENSITIVE_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                hits.append(label)
        return hits

    def work(self, context: Dict[str, Any]) -> Finding:
        findings: List[Finding] = context.get("findings", [])
        mode = context.get("llm_mode", "offline")

        exposures: List[Dict[str, Any]] = []
        for f in findings:
            text = f.summary + " " + str(f.payload)
            hits = self.scan(text)
            if hits:
                exposures.append({"agent": f.agent.value, "types": hits})

        external = mode == "cloud"
        verdict = "Разрешено"
        if exposures and external:
            verdict = "Блокирано"
        elif exposures:
            verdict = "Разрешено локално"

        self.say(f"Проверени {len(findings)} резултата; режим: {mode}; заключение: {verdict}.",
                 context.get("round", 0))
        return Finding(
            agent=self.role,
            summary=(f"Съответствие: {verdict}. Открити чувствителни елементи в "
                     f"{len(exposures)} резултата."),
            payload={"exposures": exposures, "verdict": verdict, "external": external,
                     "policy": ("При облачен режим чувствителните данни не напускат средата; "
                                "обработката се пренасочва към локален модел.")},
            confidence=1.0,
        )


class AdvisorAgent(Agent):
    """Синтезира валидирания анализ в действена препоръка."""

    role = AgentRole.ADVISOR
    description = "Формулира окончателната препоръка с обосновка."

    def work(self, context: Dict[str, Any]) -> Finding:
        findings: List[Finding] = context.get("findings", [])
        weights = context.get("weights", {})

        analyst = next((f for f in findings if f.agent == AgentRole.ANALYST), None)
        risk = next((f for f in findings if f.agent == AgentRole.RISK), None)
        critiques: List[Critique] = context.get("critiques", [])

        if not analyst:
            return Finding(agent=self.role, summary="Липсва анализ.", confidence=0.0)

        # Съответствието е предварително условие: при блокиране препоръката
        # не се издава, за да не изтече чувствителна информация.
        compliance = next((f for f in findings if f.agent == AgentRole.COMPLIANCE), None)
        if compliance and compliance.payload.get("verdict") == "Блокирано":
            text = ("Препоръката е задържана от агента за съответствие: "
                    "обработката би извела чувствителна информация извън средата. "
                    "Необходимо е преминаване към локален режим или анонимизиране "
                    "на данните преди повторно изпълнение.")
            self.say("Препоръката е задържана по съображения за поверителност.",
                     context.get("round", 0))
            return Finding(agent=self.role, summary=text,
                           payload={"recommendation": text, "withheld": True},
                           confidence=1.0)

        ranked = analyst.payload["ranked"]
        top = ranked[0]
        gaps = score_gaps(top, weights) if weights else []

        lines = [
            f"Препоръчан доставчик: {top['code']} (FAIS {top['FAIS']}, клас {top['class']}).",
        ]
        if gaps:
            weakest = gaps[0]
            lines.append(f"Най-голям потенциал за подобрение: {weakest[0]}.")
        if risk:
            red = risk.payload.get("red", [])
            hidden = risk.payload.get("hidden_risk", [])
            if red:
                lines.append(f"Доставчици с висок риск от прекъсване: {', '.join(red)}.")
            if hidden:
                codes = ", ".join(h["code"] for h in hidden)
                lines.append(f"Скрито влошаване при: {codes} — изисква наблюдение.")

        blocking = [c for c in critiques if c.blocking]
        if blocking:
            lines.append(f"Внимание: {len(blocking)} неразрешени съществени възражения — "
                         "решението подлежи на човешка валидация преди изпълнение.")
        lines.append("Окончателното решение остава отговорност на специалиста "
                     "(принцип Human-in-the-Loop).")

        text = " ".join(lines)
        self.say("Формулирана окончателна препоръка.", context.get("round", 0))
        return Finding(
            agent=self.role,
            summary=text,
            payload={"recommendation": text, "top": top},
            confidence=0.8 if blocking else 0.95,
        )
