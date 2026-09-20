"""Аналитични агенти: Данни, Оценка и Риск."""
from __future__ import annotations

from typing import Any, Dict, List

from ..core.agent_base import Agent
from ..core.aisim import (
    DIMS, DIM_NAMES, evaluate, price_ranking, score_gaps, early_warning,
)
from ..core.types import AgentRole, Finding


class DataAgent(Agent):
    """Събира и валидира входните данни."""

    role = AgentRole.DATA
    description = "Събира и валидира данните за шестте измерения; следи за липси и аномалии."

    def validate(self, suppliers: List[Dict]) -> List[str]:
        """Връща списък от установени проблеми в данните."""
        issues: List[str] = []
        for s in suppliers:
            code = s.get("code", "?")
            for d in DIMS + ["PSS", "risk_prob"]:
                v = s.get(d)
                if v is None:
                    issues.append(f"{code}: липсва стойност за {DIM_NAMES.get(d, d)}")
                elif not 0 <= float(v) <= 100:
                    issues.append(f"{code}: стойност извън диапазона 0–100 за {DIM_NAMES.get(d, d)}")
        return issues

    def work(self, context: Dict[str, Any]) -> Finding:
        suppliers = context["suppliers"]
        issues = self.validate(suppliers)
        quality = round(100 * (1 - len(issues) / max(len(suppliers) * 8, 1)), 1)
        self.say(f"Валидирани {len(suppliers)} доставчика; установени {len(issues)} проблема.",
                 context.get("round", 0))
        return Finding(
            agent=self.role,
            summary=f"Данни за {len(suppliers)} доставчика; качество на данните {quality}%.",
            payload={"issues": issues, "data_quality": quality, "count": len(suppliers)},
            confidence=quality / 100,
        )


class AnalystAgent(Agent):
    """Прилага модела AISIM и класира доставчиците."""

    role = AgentRole.ANALYST
    description = "Изчислява CSS, FAIS и класификацията по модела AISIM."

    def work(self, context: Dict[str, Any]) -> Finding:
        suppliers = context["suppliers"]
        weights = context["weights"]
        alpha = context.get("alpha", 0.60)

        ranked = evaluate(suppliers, weights, alpha)
        by_price = price_ranking(suppliers)
        price_map = {r["code"]: r["price_rank"] for r in by_price}

        # най-голямо разминаване между ценовия и интегрирания ранг
        divergence = []
        for r in ranked:
            shift = price_map[r["code"]] - r["rank"]
            divergence.append({"code": r["code"], "price_rank": price_map[r["code"]],
                               "fais_rank": r["rank"], "shift": shift})
        worst = min(divergence, key=lambda d: d["shift"])

        self.say(f"Класирани {len(ranked)} доставчика; водещ: {ranked[0]['code']} "
                 f"(FAIS {ranked[0]['FAIS']}).", context.get("round", 0))
        return Finding(
            agent=self.role,
            summary=(f"Водещ доставчик {ranked[0]['code']} с FAIS {ranked[0]['FAIS']} "
                     f"({ranked[0]['class']})."),
            payload={"ranked": ranked, "divergence": divergence,
                     "biggest_drop": worst, "alpha": alpha, "weights": weights},
            confidence=0.85,
        )


class RiskAgent(Agent):
    """Оценява риска и формира ранните предупреждения."""

    role = AgentRole.RISK
    description = "Анализира прогнозния риск, тенденциите и ранните предупреждения."

    def work(self, context: Dict[str, Any]) -> Finding:
        suppliers = context["suppliers"]
        weights = context["weights"]
        alpha = context.get("alpha", 0.60)
        ranked = evaluate(suppliers, weights, alpha)

        red, yellow, declining = [], [], []
        for r in ranked:
            w = early_warning(r["risk_prob"])
            if w == "Червено":
                red.append(r["code"])
            elif w == "Жълто":
                yellow.append(r["code"])
            if r["trend"] <= -5:
                declining.append({"code": r["code"], "trend": r["trend"],
                                  "css": r["CSS"], "pss": r["PSS"]})

        # доставчици, чиито текущи оценки са добри, но прогнозата е слаба
        hidden = [d for d in declining if d["css"] >= 80]

        self.say(f"Червени: {len(red)}; жълти: {len(yellow)}; с влошаваща се прогноза: "
                 f"{len(declining)}.", context.get("round", 0))
        return Finding(
            agent=self.role,
            summary=(f"{len(red)} доставчика с висок риск от прекъсване; "
                     f"{len(hidden)} със скрито влошаване."),
            payload={"red": red, "yellow": yellow, "declining": declining,
                     "hidden_risk": hidden},
            confidence=0.75,
        )
