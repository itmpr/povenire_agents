"""Агент „Учен" (Research / Literature Agent).

Търси и анализира научна литература по темата, извлича предложените
досега подходи и изготвя готови за дисертацията академични секции
с коректни цитати.

Работи с вградена, проверена библиотека от източници (curated corpus).
Това е съзнателно решение: то гарантира, че агентът цитира само реално
съществуващи публикации. При наличие на достъп до научни бази данни
методът `search` може да бъде разширен с реално търсене, като валидацията
на цитатите остава задължителна.
"""
from __future__ import annotations

from typing import Any, Dict, List

from ..core.agent_base import Agent
from ..core.types import AgentRole, Finding

# Проверена библиотека от реални публикации по темата
CORPUS: List[Dict[str, Any]] = [
    {
        "key": "guida2023",
        "authors": "Guida, M., Caniato, F., Moretto, A., & Ronchi, S.",
        "year": 2023,
        "title": "The role of artificial intelligence in the procurement process: State of the art and research agenda",
        "venue": "Journal of Purchasing and Supply Management, 29(2), 100823",
        "topics": ["ai", "procurement", "review"],
        "contribution": "Първи систематичен преглед на приложенията на изкуствен интелект в Purchasing процеса; съпоставя технологичните решения с утвърден процесен модел и очертава изследователска програма.",
        "relevance": "Основна рамка за категоризиране на приложенията по фази на закупуването.",
    },
    {
        "key": "baryannis2019scrm",
        "authors": "Baryannis, G., Validi, S., Dani, S., & Antoniou, G.",
        "year": 2019,
        "title": "Supply chain risk management and artificial intelligence: state of the art and future research directions",
        "venue": "International Journal of Production Research, 57(7), 2179–2202",
        "topics": ["ai", "risk", "review"],
        "contribution": "Класифицира изследванията по използвана AI методология и по задача на управлението на риска (идентифициране, оценка, реакция).",
        "relevance": "Теоретична основа за прогнозния компонент на модела.",
    },
    {
        "key": "baryannis2019tradeoff",
        "authors": "Baryannis, G., Dani, S., & Antoniou, G.",
        "year": 2019,
        "title": "Predicting supply chain risks using machine learning: The trade-off between performance and interpretability",
        "venue": "Future Generation Computer Systems, 101, 993–1004",
        "topics": ["ml", "risk", "explainability"],
        "contribution": "Демонстрира компромиса между точност и интерпретируемост при прогнозиране на риск във веригата за доставки.",
        "relevance": "Обосновава избора на обясним модел пред максимална точност при критични решения.",
    },
    {
        "key": "kosasih2024",
        "authors": "Kosasih, E. E., Papadakis, E., Baryannis, G., & Brintrup, A.",
        "year": 2024,
        "title": "A review of explainable artificial intelligence in supply chain management using neurosymbolic approaches",
        "venue": "International Journal of Production Research, 62(4), 1510–1540",
        "topics": ["explainability", "review"],
        "contribution": "Преглед на обяснимия изкуствен интелект във веригите за доставки чрез невросимволни подходи.",
        "relevance": "Подкрепя изискването за обяснимост на препоръките към специалиста.",
    },
    {
        "key": "abdulla2023",
        "authors": "Abdulla, A., Baryannis, G., & Badi, I.",
        "year": 2023,
        "title": "An integrated machine learning and MARCOS method for supplier evaluation and selection",
        "venue": "Decision Analytics Journal, 8, 100305",
        "topics": ["ml", "supplier-selection", "mcdm"],
        "contribution": "Интегрира машинно обучение с многокритериален метод за оценка и избор на доставчици.",
        "relevance": "Най-близкият предшественик на предложения модел; показва жизнеспособността на хибридния подход MCDM + ML.",
    },
    {
        "key": "toorajipour2021",
        "authors": "Toorajipour, R., Sohrabpour, V., Nazarpour, A., Oghazi, P., & Fischl, M.",
        "year": 2021,
        "title": "Artificial intelligence in supply chain management: A systematic literature review",
        "venue": "Journal of Business Research, 122, 502–517",
        "topics": ["ai", "review"],
        "contribution": "Систематичен преглед, идентифициращ машинното обучение като доминираща методология в управлението на веригите за доставки.",
        "relevance": "Контекст за избора на алгоритмичен подход.",
    },
    {
        "key": "dickson1966",
        "authors": "Dickson, G. W.",
        "year": 1966,
        "title": "An analysis of vendor selection systems and decisions",
        "venue": "Journal of Purchasing, 2(1), 5–17",
        "topics": ["supplier-selection", "classic"],
        "contribution": "Идентифицира 23 критерия за избор на доставчик, сред които качеството, доставката и цената са водещи.",
        "relevance": "Историческа основа на многокритериалния подход.",
    },
    {
        "key": "weber1991",
        "authors": "Weber, C. A., Current, J. R., & Benton, W. C.",
        "year": 1991,
        "title": "Vendor selection criteria and methods",
        "venue": "European Journal of Operational Research, 50(1), 2–18",
        "topics": ["supplier-selection", "review"],
        "contribution": "Систематизира критериите и методите за избор на доставчик.",
        "relevance": "Утвърждава многокритериалната постановка на задачата.",
    },
    {
        "key": "deboer2001",
        "authors": "De Boer, L., Labro, E., & Morlacchi, P.",
        "year": 2001,
        "title": "A review of methods supporting supplier selection",
        "venue": "European Journal of Purchasing & Supply Management, 7(2), 75–89",
        "topics": ["supplier-selection", "review"],
        "contribution": "Предлага рамка на методите, подпомагащи избора на доставчик, по фази на решението.",
        "relevance": "Методологична рамка за позициониране на предложения модел.",
    },
    {
        "key": "ho2010",
        "authors": "Ho, W., Xu, X., & Dey, P. K.",
        "year": 2010,
        "title": "Multi-criteria decision making approaches for supplier evaluation and selection: A literature review",
        "venue": "European Journal of Operational Research, 202(1), 16–24",
        "topics": ["mcdm", "supplier-selection", "review"],
        "contribution": "Документира доминирането на многокритериалните методи (AHP, TOPSIS, размити разширения).",
        "relevance": "Обосновава претеглената структура на текущата оценка.",
    },
    {
        "key": "kraljic1983",
        "authors": "Kraljic, P.",
        "year": 1983,
        "title": "Purchasing must become supply management",
        "venue": "Harvard Business Review, 61(5), 109–117",
        "topics": ["strategy", "classic"],
        "contribution": "Поставя началото на стратегическото управление на снабдяването с диференциация по риск и значимост.",
        "relevance": "Обосновава адаптивните тегла според критичността на компонента.",
    },
    {
        "key": "ellram1995",
        "authors": "Ellram, L. M.",
        "year": 1995,
        "title": "Total cost of ownership: An analysis approach for purchasing",
        "venue": "International Journal of Physical Distribution & Logistics Management, 25(8), 4–23",
        "topics": ["tco", "cost"],
        "contribution": "Формализира общата стойност на притежание като аналитичен подход в закупуването.",
        "relevance": "Икономическата обосновка защо цената сама по себе си е непълен показател.",
    },
    {
        "key": "vlachos2025",
        "authors": "Vlachos, I., & Reddy, P. G.",
        "year": 2025,
        "title": "Machine learning in supply chain management: systematic literature review and future research agenda",
        "venue": "International Journal of Production Research",
        "topics": ["ml", "review"],
        "contribution": "Актуален систематичен преглед, потвърждаващ зрелостта на машинното обучение в управлението на веригите.",
        "relevance": "Актуализира състоянието на изследванията.",
    },
]


class ResearcherAgent(Agent):
    """Търси литература, синтезира съществуващите подходи и пише секции."""

    role = AgentRole.RESEARCHER
    description = ("Търси и чете научни статии по темата, извлича вече "
                   "предложените подходи и изготвя академични секции с цитати.")

    def search(self, topics: List[str] | None = None) -> List[Dict[str, Any]]:
        """Връща релевантните публикации по зададени теми."""
        if not topics:
            return list(CORPUS)
        return [p for p in CORPUS if any(t in p["topics"] for t in topics)]

    def citation(self, paper: Dict[str, Any]) -> str:
        """Пълно библиографско описание."""
        return (f"{paper['authors']} ({paper['year']}). {paper['title']}. "
                f"{paper['venue']}.")

    def inline(self, paper: Dict[str, Any]) -> str:
        """Цитат в текста, например: (Guida et al., 2023)."""
        first = paper["authors"].split(",")[0].strip()
        multi = paper["authors"].count("&") or paper["authors"].count(",") > 1
        return f"({first}{' et al.' if multi else ''}, {paper['year']})"

    def synthesize_gap(self, papers: List[Dict[str, Any]]) -> str:
        """Формулира изследователския пропуск спрямо намереното."""
        has_mcdm = any("mcdm" in p["topics"] for p in papers)
        has_ml = any("ml" in p["topics"] for p in papers)
        has_xai = any("explainability" in p["topics"] for p in papers)
        parts = []
        if has_mcdm:
            parts.append("многокритериалното оценяване е зряло направление")
        if has_ml:
            parts.append("машинното обучение се прилага успешно за прогнозиране на риск")
        if has_xai:
            parts.append("обяснимостта е признат, но недостатъчно операционализиран изискване")
        body = "; ".join(parts) if parts else "литературата е фрагментирана"
        return (f"Литературата показва, че {body}. Установеният пропуск е липсата на "
                "интегриран модел, който едновременно съчетава многокритериална текуща "
                "оценка с предиктивен компонент, запазва обяснимост и е реализиран в "
                "действащ софтуер с икономическа оценка.")

    def write_section(self, topics: List[str] | None = None) -> str:
        """Съставя готов за дисертацията академичен текст."""
        papers = self.search(topics)
        papers = sorted(papers, key=lambda p: p["year"])
        lines = []
        for p in papers:
            lines.append(f"{p['contribution']} {self.inline(p)}")
        gap = self.synthesize_gap(papers)
        return " ".join(lines) + " " + gap

    # ---------- научен надзор над разработката ----------

    def review_methodology(self, context: Dict[str, Any]) -> List[str]:
        """Проверява методологията на модела спрямо литературата.

        Връща списък от методологични бележки към разработката.
        """
        notes: List[str] = []
        weights = context.get("weights", {})
        alpha = context.get("alpha", 0.60)
        suppliers = context.get("suppliers", [])

        total = round(sum(weights.values()), 3) if weights else 0
        if weights and abs(total - 1.0) > 1e-6:
            notes.append(f"Сумата на теглата е {total}, а следва да бъде 1,0 — "
                         "нарушава се условието за нормираност на претеглената оценка.")

        if not 0.0 <= alpha <= 1.0:
            notes.append(f"Коефициентът α = {alpha} е извън допустимия диапазон [0, 1].")
        elif alpha < 0.5:
            notes.append(f"При α = {alpha} прогнозният компонент надделява над доказаното "
                         "представяне; литературата за компромиса точност–интерпретируемост "
                         "(Baryannis, Dani & Antoniou, 2019) препоръчва предпазливост.")

        if len(suppliers) < 30:
            notes.append(f"Извадката от {len(suppliers)} доставчика е недостатъчна за "
                         "статистическо обобщение; резултатите следва да се представят "
                         "като доказване на концепцията (Proof of Concept).")

        if context.get("pss_source", "simulated") == "simulated":
            notes.append("Прогнозната оценка (PSS) е симулирана. За емпирична валидност е "
                         "необходим обучен модел върху исторически данни, включващи "
                         "настъпили инциденти като целева променлива.")
        return notes

    def propose_approaches(self, context: Dict[str, Any]) -> List[Dict[str, str]]:
        """Предлага нови подходи за решаване, обосновани с литературата."""
        proposals = [
            {
                "title": "Хибриден подход MCDM + машинно обучение",
                "rationale": "Интегрирането на многокритериален метод с обучен класификатор "
                             "е демонстрирано като жизнеспособно за оценка на доставчици.",
                "source": "Abdulla, Baryannis & Badi (2023)",
                "action": "Заместване на симулирания PSS с класификатор (Random Forest / "
                          "XGBoost), обучен върху исторически инциденти.",
            },
            {
                "title": "Обяснимост чрез приносни стойности",
                "rationale": "Обяснимостта е признато изискване при критични решения във "
                             "веригите за доставки.",
                "source": "Kosasih, Papadakis, Baryannis & Brintrup (2024)",
                "action": "Добавяне на метод за приносен анализ (SHAP), който разкрива "
                          "приноса на всяко измерение към конкретната прогноза.",
            },
            {
                "title": "Анализ на чувствителността на теглата",
                "rationale": "Устойчивостта на класирането при промяна на теглата е "
                             "индикатор за надеждност на многокритериалния модел.",
                "source": "Ho, Xu & Dey (2010)",
                "action": "Систематично вариране на теглата и измерване на стабилността "
                          "на първите позиции в класирането.",
            },
            {
                "title": "Разширяване към многостепенна видимост (Tier-n)",
                "rationale": "Значителна част от риска се намира отвъд доставчиците от "
                             "първо ниво и остава невидима при класическия анализ.",
                "source": "Baryannis, Validi, Dani & Antoniou (2019)",
                "action": "Моделиране на зависимостите между нивата за откриване на скрит "
                          "единствен източник (hidden single source).",
            },
            {
                "title": "Оценка, коригирана спрямо риска",
                "rationale": "Общата стойност на притежание следва да включва очакваната "
                             "стойност на риска, а не само преките разходи.",
                "source": "Ellram (1995)",
                "action": "Въвеждане на Risk-adjusted TCO = TCO + вероятност × финансов ефект.",
            },
        ]
        return proposals

    def llm_commentary(self, papers: List[Dict[str, Any]], gap: str,
                        notes: List[str]) -> str:
        """Помолва езиковия модел (ако е наличен) за кратък обобщаващ коментар.

        Моделът получава само вече установените факти (приноси на
        публикациите, пропуска, методологичните бележки) и е изрично
        инструктиран да не добавя нови цитати — той перифразира, а не
        генерира съдържание. При липса на модел или грешка във връзката
        (напр. Ollama не работи) методът тихо връща празен низ, за да не
        наруши детерминистичния анализ.
        """
        system = ("Ти си научен сътрудник. Пиши само на български, кратко "
                   "(3-4 изречения), без да добавяш нови факти, източници или "
                   "цитати извън предоставените.")
        facts = "\n".join(f"- {p['contribution']}" for p in papers)
        prompt = (f"Установени приноси на прегледаната литература:\n{facts}\n\n"
                  f"Изследователски пропуск: {gap}\n\n"
                  f"Методологични бележки: {'; '.join(notes) if notes else 'няма'}\n\n"
                  "Напиши кратък обобщаващ коментар за читателя.")
        try:
            return self.llm.complete(system, prompt).strip()
        except Exception:                                   # noqa: BLE001
            return ""

    def work(self, context: Dict[str, Any]) -> Finding:
        topics = context.get("topics")
        papers = self.search(topics)
        section = self.write_section(topics)
        notes = self.review_methodology(context)
        proposals = self.propose_approaches(context)
        gap = self.synthesize_gap(papers)
        commentary = self.llm_commentary(papers, gap, notes)

        self.say(f"Прегледани {len(papers)} публикации; {len(notes)} методологични бележки; "
                 f"{len(proposals)} предложени подхода.", context.get("round", 0))
        return Finding(
            agent=self.role,
            summary=(f"Литературен обзор: {len(papers)} публикации, {len(notes)} методологични "
                     f"бележки, {len(proposals)} предложения за развитие."),
            payload={
                "papers": papers,
                "section_text": section,
                "gap": gap,
                "bibliography": [self.citation(p) for p in papers],
                "methodology_notes": notes,
                "proposals": proposals,
                "llm_commentary": commentary,
            },
            sources=[self.citation(p) for p in papers],
            confidence=0.9,
        )

    def revise(self, finding, critiques, context):
        """При критика за недостатъчно покритие разширява обхвата."""
        if not critiques:
            return finding
        all_papers = self.search(None)
        finding.payload["papers"] = all_papers
        finding.payload["section_text"] = self.write_section(None)
        finding.payload["bibliography"] = [self.citation(p) for p in all_papers]
        finding.sources = finding.payload["bibliography"]
        finding.summary = (f"Литературен обзор (разширен): {len(all_papers)} публикации.")
        finding.revised = True
        return finding
