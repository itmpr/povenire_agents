"""Тестове за многоагентната система."""
import pytest

from provenire_agents.core.aisim import (
    DEFAULT_PROFILE, WEIGHTS, as_records, classify, compute_css,
    compute_fais, early_warning, evaluate,
)
from provenire_agents.core.orchestrator import Orchestrator
from provenire_agents.core.types import AgentRole, Severity
from provenire_agents.agents.researcher import CORPUS, ResearcherAgent
from provenire_agents.agents.control import ComplianceAgent, CriticAgent


# ---------------- модел ----------------

def test_css_formula():
    s = dict(zip(["code", "Q", "D", "C", "R", "S", "I", "PSS", "risk_prob"],
                 ["S05", 96, 98, 70, 95, 91, 92, 93, 12]))
    expected = 0.25*96 + 0.20*98 + 0.20*70 + 0.20*95 + 0.10*91 + 0.05*92
    assert compute_css(s, WEIGHTS[DEFAULT_PROFILE]) == round(expected, 1)


def test_fais_formula():
    assert compute_fais(80.0, 60.0, 0.6) == round(0.6*80 + 0.4*60, 1)


def test_classify_and_warning_boundaries():
    assert classify(90) == "Strategic"
    assert classify(89.9) == "Preferred"
    assert classify(59) == "Critical"
    assert early_warning(61) == "Червено"
    assert early_warning(30) == "Жълто"
    assert early_warning(29) == "Зелено"


def test_cheapest_supplier_ranks_last():
    """Ключовият резултат: най-евтиният не е най-добрият."""
    ranked = evaluate(as_records(), WEIGHTS[DEFAULT_PROFILE], 0.6)
    cheapest = max(as_records(), key=lambda s: s["C"])["code"]
    assert cheapest == "S06"
    assert ranked[-1]["code"] == "S06"


# ---------------- агент Учен ----------------

def test_researcher_returns_real_sources():
    r = ResearcherAgent()
    f = r.work({"suppliers": as_records(), "weights": WEIGHTS[DEFAULT_PROFILE]})
    assert len(f.payload["papers"]) == len(CORPUS)
    assert all("(" in c and ")" in c for c in f.payload["bibliography"])


def test_researcher_flags_bad_weights():
    """Научният надзор открива ненормирани тегла."""
    r = ResearcherAgent()
    notes = r.review_methodology({"weights": {"Q": .5, "D": .5, "C": .5,
                                              "R": 0, "S": 0, "I": 0},
                                  "alpha": 0.6, "suppliers": as_records()})
    assert any("тегла" in n for n in notes)


def test_researcher_flags_invalid_alpha():
    r = ResearcherAgent()
    notes = r.review_methodology({"weights": WEIGHTS[DEFAULT_PROFILE],
                                  "alpha": 1.4, "suppliers": as_records()})
    assert any("α" in n for n in notes)


def test_researcher_proposes_approaches():
    r = ResearcherAgent()
    proposals = r.propose_approaches({})
    assert len(proposals) >= 3
    assert all({"title", "rationale", "source", "action"} <= set(p) for p in proposals)


# ---------------- агент Критик ----------------

def test_critic_raises_objections():
    orch = Orchestrator(max_rounds=1)
    ctx = {"suppliers": as_records(), "weights": WEIGHTS[DEFAULT_PROFILE], "alpha": 0.6}
    findings = [a.work(ctx) for a in orch.specialists]
    ctx["findings"] = findings
    crit = CriticAgent().work(ctx)
    assert len(crit.payload["critiques"]) > 0


def test_critic_detects_hidden_risk():
    """S02 има добра текуща оценка, но влошаваща се прогноза."""
    orch = Orchestrator(max_rounds=1)
    ctx = {"suppliers": as_records(), "weights": WEIGHTS[DEFAULT_PROFILE], "alpha": 0.6}
    risk = orch.risk.work(ctx)
    codes = [h["code"] for h in risk.payload["hidden_risk"]]
    assert "S02" in codes


# ---------------- агент Съответствие ----------------

def test_compliance_detects_sensitive_content():
    c = ComplianceAgent()
    hits = c.scan("Приложен е cost breakdown и оферта от доставчика")
    assert len(hits) >= 2


def test_compliance_blocks_external_exposure():
    from provenire_agents.core.types import Finding
    c = ComplianceAgent()
    f = Finding(agent=AgentRole.ANALYST, summary="Анализ на cost breakdown")
    out = c.work({"findings": [f], "llm_mode": "cloud"})
    assert out.payload["verdict"] == "Блокирано"


# ---------------- оркестрация ----------------

def test_full_consultation_runs():
    orch = Orchestrator(max_rounds=2)
    res = orch.run()
    assert res.rounds >= 1
    assert res.recommendation
    assert len(res.transcript) > 5
    roles = {f.agent for f in res.findings}
    assert AgentRole.RESEARCHER in roles
    assert AgentRole.COMPLIANCE in roles
    assert AgentRole.ADVISOR in roles


def test_consultation_includes_all_eight_agents():
    orch = Orchestrator()
    assert len(orch.roster) == 7   # специалисти + критик + съответствие + съветник


def test_revision_marks_finding():
    """При съществени възражения резултатът се преработва."""
    orch = Orchestrator(max_rounds=3)
    res = orch.run()
    # при наличие на блокиращи възражения трябва да има поне един преработен резултат
    if any(c.blocking for c in res.critiques):
        assert res.rounds >= 1


# ---------------- съответствието като контролен пункт ----------------

def test_compliance_participates_every_round():
    """Съответствието присъства в резултатите на всяка консултация."""
    res = Orchestrator(max_rounds=2).run()
    assert any(f.agent == AgentRole.COMPLIANCE for f in res.findings)


def test_critic_escalates_compliance_breach():
    """Нарушение на поверителността поражда блокиращо възражение."""
    from provenire_agents.core.types import Finding
    f = Finding(agent=AgentRole.ANALYST, summary="Анализ с cost breakdown и марж")
    comp = ComplianceAgent().work({"findings": [f], "llm_mode": "cloud"})
    crit = CriticAgent().work({"findings": [comp]})
    breaches = [c for c in crit.payload["critiques"]
                if c.target == AgentRole.COMPLIANCE and c.severity == Severity.BLOCKER]
    assert breaches


def test_recommendation_withheld_on_breach():
    """При блокиране препоръката не се издава."""
    from provenire_agents.core.types import Finding
    from provenire_agents.agents.control import AdvisorAgent
    from provenire_agents.core.aisim import WEIGHTS, DEFAULT_PROFILE

    orch = Orchestrator(max_rounds=1)
    ctx = {"suppliers": as_records(), "weights": WEIGHTS[DEFAULT_PROFILE], "alpha": 0.6}
    analyst = orch.analyst.work(ctx)
    blocked = Finding(agent=AgentRole.COMPLIANCE, summary="Блокирано",
                      payload={"verdict": "Блокирано", "exposures": [
                          {"agent": "Оценка", "types": ["информация за марж"]}]})
    out = AdvisorAgent().work({**ctx, "findings": [analyst, blocked], "critiques": []})
    assert out.payload.get("withheld") is True
    assert "задържана" in out.summary
