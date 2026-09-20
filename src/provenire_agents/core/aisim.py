"""AI Supplier Intelligence Model (AISIM) — изчислително ядро.

    CSS  = Σ wᵢ · dimᵢ                (текуща оценка)
    FAIS = α · CSS + (1 − α) · PSS    (крайна оценка)
"""
from __future__ import annotations

from typing import Dict, List, Tuple

DIMS = ["Q", "D", "C", "R", "S", "I"]

DIM_NAMES = {
    "Q": "Качество", "D": "Доставка", "C": "Цена",
    "R": "Риск", "S": "Устойчивост", "I": "Иновации",
}

WEIGHTS = {
    "AISIM (по подразбиране)":   {"Q": .25, "D": .20, "C": .20, "R": .20, "S": .10, "I": .05},
    "Safety-critical компонент": {"Q": .35, "D": .20, "C": .10, "R": .25, "S": .05, "I": .05},
    "Стандартен компонент":      {"Q": .20, "D": .20, "C": .30, "R": .15, "S": .10, "I": .05},
}

DEFAULT_PROFILE = "AISIM (по подразбиране)"
DEFAULT_ALPHA = 0.60

CLASSES: List[Tuple[float, str]] = [
    (90, "Strategic"), (80, "Preferred"), (70, "Controlled"),
    (60, "High Risk"), (0, "Critical"),
]

# Примерни доставчици: код, Q, D, C, R, S, I, PSS, вероятност за риск (%)
SAMPLE_SUPPLIERS = [
    ["S01", 95, 92, 78, 94, 90, 88, 91, 15],
    ["S02", 83, 97, 96, 60, 72, 80, 64, 68],
    ["S03", 91, 89, 86, 90, 94, 85, 90, 18],
    ["S04", 88, 84, 92, 75, 82, 75, 82, 35],
    ["S05", 96, 98, 70, 95, 91, 92, 93, 12],
    ["S06", 77, 82, 98, 58, 68, 70, 69, 58],
    ["S07", 92, 94, 84, 88, 87, 95, 91, 14],
    ["S08", 86, 79, 90, 69, 77, 83, 76, 40],
    ["S09", 89, 91, 82, 86, 96, 89, 89, 20],
    ["S10", 81, 88, 94, 72, 73, 78, 78, 33],
]

SUPPLIER_FIELDS = ["code"] + DIMS + ["PSS", "risk_prob"]


def as_records() -> List[Dict]:
    """Примерните доставчици като списък от речници."""
    return [dict(zip(SUPPLIER_FIELDS, row)) for row in SAMPLE_SUPPLIERS]


def compute_css(s: Dict, weights: Dict[str, float]) -> float:
    """Текуща оценка — претеглена сума на шестте измерения."""
    return round(sum(s[d] * weights[d] for d in DIMS), 1)


def compute_fais(css: float, pss: float, alpha: float = DEFAULT_ALPHA) -> float:
    """Крайна оценка — комбинация от текущо и прогнозно представяне."""
    return round(alpha * css + (1 - alpha) * pss, 1)


def classify(fais: float) -> str:
    for low, label in CLASSES:
        if fais >= low:
            return label
    return CLASSES[-1][1]


def early_warning(risk_prob: float) -> str:
    if risk_prob > 60:
        return "Червено"
    if risk_prob >= 30:
        return "Жълто"
    return "Зелено"


def evaluate(suppliers: List[Dict], weights: Dict[str, float],
             alpha: float = DEFAULT_ALPHA) -> List[Dict]:
    """Прилага целия модел и връща класирани доставчици."""
    out = []
    for s in suppliers:
        row = dict(s)
        row["CSS"] = compute_css(s, weights)
        row["FAIS"] = compute_fais(row["CSS"], s["PSS"], alpha)
        row["class"] = classify(row["FAIS"])
        row["warning"] = early_warning(s["risk_prob"])
        row["trend"] = round(s["PSS"] - row["CSS"], 1)
        out.append(row)
    out.sort(key=lambda r: r["FAIS"], reverse=True)
    for i, r in enumerate(out, 1):
        r["rank"] = i
    return out


def price_ranking(suppliers: List[Dict]) -> List[Dict]:
    """Класиране само по цена — за съпоставка с интегрирания модел."""
    ranked = sorted(suppliers, key=lambda s: s["C"], reverse=True)
    return [{**s, "price_rank": i} for i, s in enumerate(ranked, 1)]


def score_gaps(s: Dict, weights: Dict[str, float]) -> List[Tuple[str, float]]:
    """Кои измерения теглят оценката надолу (обяснимост)."""
    gaps = [(DIM_NAMES[d], round(weights[d] * (100 - s[d]), 2)) for d in DIMS]
    gaps.sort(key=lambda x: x[1], reverse=True)
    return gaps
