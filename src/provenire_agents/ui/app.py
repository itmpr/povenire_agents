"""Provenire Agents — настолно приложение за Windows (tkinter).

Интерфейсът показва консултацията между агентите в реално време,
класирането на доставчиците, възраженията на Критика и научния обзор.
"""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Dict, List, Optional

from ..core.aisim import DEFAULT_ALPHA, DEFAULT_PROFILE, WEIGHTS, as_records
from ..core.agent_base import LocalLLM, OfflineLLM
from ..core.orchestrator import Orchestrator
from ..core.types import AgentRole, ConsultationResult, Message

TEAL = "#0E7C7B"
BG = "#F4F6F7"
DARK = "#14181B"

ROLE_COLORS = {
    AgentRole.ORCHESTRATOR: "#5A6266",
    AgentRole.RESEARCHER: "#6A4C93",
    AgentRole.DATA: "#1B6CA8",
    AgentRole.ANALYST: "#0E7C7B",
    AgentRole.RISK: "#C1662F",
    AgentRole.CRITIC: "#B3261E",
    AgentRole.COMPLIANCE: "#5C6F3A",
    AgentRole.ADVISOR: "#2D6A4F",
}


class ProvenireApp(tk.Tk):
    """Главен прозорец на приложението."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Provenire Agents — Интелигентна оценка на доставчици")
        self.geometry("1180x760")
        self.minsize(960, 640)
        self.configure(bg=BG)

        self.queue: "queue.Queue[Any]" = queue.Queue()
        self.result: Optional[ConsultationResult] = None
        self.suppliers: List[Dict] = as_records()
        self.running = False

        self._build_style()
        self._build_header()
        self._build_controls()
        self._build_tabs()
        self._build_status()

        self.after(100, self._drain_queue)

    # ---------------- оформление ----------------

    def _build_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", padding=(14, 7), font=("Segoe UI", 10))
        style.map("TNotebook.Tab", background=[("selected", TEAL)],
                  foreground=[("selected", "white")])
        style.configure("Treeview", rowheight=24, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
        style.configure("Run.TButton", font=("Segoe UI", 10, "bold"))

    def _build_header(self) -> None:
        head = tk.Frame(self, bg=BG)
        head.pack(fill="x", padx=16, pady=(12, 4))
        tk.Label(head, text="PROVENIRE", font=("Segoe UI", 20, "bold"),
                 fg=DARK, bg=BG).pack(side="left")
        tk.Label(head, text="  многоагентна система за оценка на доставчици",
                 font=("Segoe UI", 10), fg="#7A8288", bg=BG).pack(side="left", pady=(8, 0))
        tk.Frame(self, height=2, bg=TEAL).pack(fill="x", padx=16)

    def _build_controls(self) -> None:
        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=16, pady=10)

        tk.Label(bar, text="Профил:", bg=BG, font=("Segoe UI", 9)).pack(side="left")
        self.profile_var = tk.StringVar(value=DEFAULT_PROFILE)
        ttk.Combobox(bar, textvariable=self.profile_var, values=list(WEIGHTS),
                     state="readonly", width=26).pack(side="left", padx=(4, 14))

        tk.Label(bar, text="α:", bg=BG, font=("Segoe UI", 9)).pack(side="left")
        self.alpha_var = tk.DoubleVar(value=DEFAULT_ALPHA)
        self.alpha_lbl = tk.Label(bar, text=f"{DEFAULT_ALPHA:.2f}", bg=BG,
                                  font=("Segoe UI", 9, "bold"), width=4)
        tk.Scale(bar, from_=0.0, to=1.0, resolution=0.05, orient="horizontal",
                 variable=self.alpha_var, showvalue=False, length=110, bg=BG,
                 highlightthickness=0, command=self._on_alpha).pack(side="left", padx=4)
        self.alpha_lbl.pack(side="left", padx=(0, 14))

        tk.Label(bar, text="Модел:", bg=BG, font=("Segoe UI", 9)).pack(side="left")
        self.mode_var = tk.StringVar(value="offline")
        ttk.Combobox(bar, textvariable=self.mode_var,
                     values=["offline", "local", "cloud"], state="readonly",
                     width=10).pack(side="left", padx=(4, 14))

        ttk.Button(bar, text="Зареди данни…", command=self._load_csv).pack(side="left")
        self.run_btn = ttk.Button(bar, text="▶  Стартирай консултация",
                                  style="Run.TButton", command=self._run)
        self.run_btn.pack(side="right")

    def _build_tabs(self) -> None:
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        # --- дневник на консултацията ---
        f1 = tk.Frame(self.nb, bg="white")
        self.log = tk.Text(f1, wrap="word", font=("Consolas", 9), bg="white",
                           relief="flat", padx=10, pady=8)
        sb = ttk.Scrollbar(f1, command=self.log.yview)
        self.log.configure(yscrollcommand=sb.set, state="disabled")
        sb.pack(side="right", fill="y")
        self.log.pack(fill="both", expand=True)
        for role, color in ROLE_COLORS.items():
            self.log.tag_configure(role.value, foreground=color, font=("Consolas", 9, "bold"))
        self.log.tag_configure("body", foreground=DARK, font=("Consolas", 9))
        self.nb.add(f1, text="  Консултация  ")

        # --- класиране ---
        f2 = tk.Frame(self.nb, bg="white")
        cols = ("rank", "code", "CSS", "PSS", "FAIS", "trend", "class", "warning")
        heads = ("№", "Доставчик", "CSS", "PSS", "FAIS", "Тренд", "Клас", "Предупреждение")
        self.tree = ttk.Treeview(f2, columns=cols, show="headings", height=16)
        for c, h in zip(cols, heads):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=100, anchor="center")
        self.tree.column("code", width=110)
        self.tree.column("class", width=120)
        self.tree.column("warning", width=130)
        self.tree.tag_configure("red", background="#FDECEA")
        self.tree.tag_configure("yellow", background="#FFF8E1")
        self.tree.tag_configure("green", background="#EDF7ED")
        self.tree.pack(fill="both", expand=True, padx=8, pady=8)
        self.nb.add(f2, text="  Класиране  ")

        # --- критика ---
        f3 = tk.Frame(self.nb, bg="white")
        self.crit = tk.Text(f3, wrap="word", font=("Segoe UI", 9), bg="white",
                            relief="flat", padx=10, pady=8, state="disabled")
        self.crit.tag_configure("blocker", foreground="#B3261E", font=("Segoe UI", 9, "bold"))
        self.crit.tag_configure("major", foreground="#C1662F", font=("Segoe UI", 9, "bold"))
        self.crit.tag_configure("minor", foreground="#5A6266")
        self.crit.tag_configure("body", foreground=DARK)
        self.crit.pack(fill="both", expand=True)
        self.nb.add(f3, text="  Възражения  ")

        # --- научен обзор ---
        f4 = tk.Frame(self.nb, bg="white")
        self.res = tk.Text(f4, wrap="word", font=("Segoe UI", 9), bg="white",
                           relief="flat", padx=10, pady=8, state="disabled")
        self.res.tag_configure("h", foreground=TEAL, font=("Segoe UI", 11, "bold"))
        self.res.tag_configure("sub", foreground=DARK, font=("Segoe UI", 9, "bold"))
        self.res.tag_configure("body", foreground=DARK)
        self.res.pack(fill="both", expand=True)
        self.nb.add(f4, text="  Научен обзор  ")

        # --- препоръка ---
        f5 = tk.Frame(self.nb, bg="white")
        self.rec = tk.Text(f5, wrap="word", font=("Segoe UI", 10), bg="white",
                           relief="flat", padx=14, pady=12, state="disabled")
        self.rec.tag_configure("h", foreground=TEAL, font=("Segoe UI", 13, "bold"))
        self.rec.tag_configure("body", foreground=DARK, font=("Segoe UI", 10))
        self.rec.pack(fill="both", expand=True)
        btnbar = tk.Frame(f5, bg="white")
        btnbar.pack(fill="x", pady=(0, 8))
        ttk.Button(btnbar, text="Експорт на отчет…",
                   command=self._export).pack(side="right", padx=12)
        self.nb.add(f5, text="  Препоръка  ")

    def _build_status(self) -> None:
        self.status = tk.Label(self, text="Готово.", anchor="w", bg="#E3E8EA",
                               fg=DARK, font=("Segoe UI", 9), padx=10, pady=4)
        self.status.pack(fill="x", side="bottom")

    # ---------------- действия ----------------

    def _on_alpha(self, _v: str) -> None:
        self.alpha_lbl.config(text=f"{self.alpha_var.get():.2f}")

    def _load_csv(self) -> None:
        path = filedialog.askopenfilename(
            title="Изберете файл с данни",
            filetypes=[("CSV файлове", "*.csv"), ("Всички файлове", "*.*")])
        if not path:
            return
        try:
            import csv
            with open(path, newline="", encoding="utf-8-sig") as fh:
                rows = list(csv.DictReader(fh))
            parsed = []
            for r in rows:
                rec = {"code": r.get("code") or r.get("supplier") or "?"}
                for k in ("Q", "D", "C", "R", "S", "I", "PSS", "risk_prob"):
                    rec[k] = float(r[k])
                parsed.append(rec)
            if not parsed:
                raise ValueError("Файлът не съдържа записи.")
            self.suppliers = parsed
            self._set_status(f"Заредени {len(parsed)} доставчика от {path}")
        except Exception as exc:                       # noqa: BLE001
            messagebox.showerror("Грешка при зареждане", str(exc))

    def _set_status(self, text: str) -> None:
        self.status.config(text=text)

    def _run(self) -> None:
        if self.running:
            return
        self.running = True
        self.run_btn.config(state="disabled")
        for widget in (self.log, self.crit, self.res, self.rec):
            widget.config(state="normal")
            widget.delete("1.0", "end")
            widget.config(state="disabled")
        self.tree.delete(*self.tree.get_children())
        self._set_status("Консултацията тече…")
        self.nb.select(0)

        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self) -> None:
        try:
            mode = self.mode_var.get()
            llm = LocalLLM() if mode == "local" else OfflineLLM()
            orch = Orchestrator(llm=llm, max_rounds=3)
            result = orch.run(
                question="Оцени и класирай доставчиците",
                suppliers=self.suppliers,
                profile=self.profile_var.get(),
                alpha=self.alpha_var.get(),
                llm_mode=mode,
                on_event=lambda m: self.queue.put(("msg", m)),
            )
            self.queue.put(("done", result))
        except Exception as exc:                       # noqa: BLE001
            self.queue.put(("error", str(exc)))

    def _drain_queue(self) -> None:
        try:
            while True:
                kind, payload = self.queue.get_nowait()
                if kind == "msg":
                    self._append_msg(payload)
                elif kind == "done":
                    self._finish(payload)
                elif kind == "error":
                    messagebox.showerror("Грешка", payload)
                    self.running = False
                    self.run_btn.config(state="normal")
                    self._set_status("Грешка при изпълнение.")
        except queue.Empty:
            pass
        self.after(100, self._drain_queue)

    def _append_msg(self, msg: Message) -> None:
        self.log.config(state="normal")
        self.log.insert("end", f"{msg.sender.value}: ", msg.sender.value)
        self.log.insert("end", f"{msg.content}\n", "body")
        self.log.see("end")
        self.log.config(state="disabled")

    def _finish(self, result: ConsultationResult) -> None:
        self.result = result
        self.running = False
        self.run_btn.config(state="normal")

        # класиране
        analyst = result.finding_by(AgentRole.ANALYST)
        if analyst:
            for r in analyst.payload["ranked"]:
                tag = {"Червено": "red", "Жълто": "yellow"}.get(r["warning"], "green")
                self.tree.insert("", "end", tags=(tag,), values=(
                    r["rank"], r["code"], r["CSS"], r["PSS"], r["FAIS"],
                    f"{r['trend']:+.1f}", r["class"], r["warning"]))

        # възражения
        self.crit.config(state="normal")
        if not result.critiques:
            self.crit.insert("end", "Няма повдигнати възражения.\n", "body")
        for c in result.critiques:
            tag = {"blocker": "blocker", "major": "major"}.get(c.severity.value, "minor")
            self.crit.insert("end", f"[{c.severity.value.upper()}] ", tag)
            self.crit.insert("end", f"{c.target.value}\n", "body")
            self.crit.insert("end", f"    Проблем: {c.issue}\n", "body")
            self.crit.insert("end", f"    Предложение: {c.suggestion}\n\n", "body")
        self.crit.config(state="disabled")

        # научен обзор
        rf = result.finding_by(AgentRole.RESEARCHER)
        self.res.config(state="normal")
        if rf:
            commentary = rf.payload.get("llm_commentary", "")
            if commentary:
                self.res.insert("end", "AI коментар (локален модел)\n", "h")
                self.res.insert("end", commentary + "\n\n", "body")
            self.res.insert("end", "Литературен обзор\n", "h")
            self.res.insert("end", rf.payload.get("section_text", "") + "\n\n", "body")
            self.res.insert("end", "Методологични бележки\n", "h")
            for n in rf.payload.get("methodology_notes", []) or ["Няма бележки."]:
                self.res.insert("end", f"  • {n}\n", "body")
            self.res.insert("end", "\nПредложени подходи\n", "h")
            for pr in rf.payload.get("proposals", []):
                self.res.insert("end", f"  {pr['title']}\n", "sub")
                self.res.insert("end", f"    Обосновка: {pr['rationale']}\n", "body")
                self.res.insert("end", f"    Източник: {pr['source']}\n", "body")
                self.res.insert("end", f"    Действие: {pr['action']}\n\n", "body")
            self.res.insert("end", "Библиография\n", "h")
            for b in rf.payload.get("bibliography", []):
                self.res.insert("end", f"  • {b}\n", "body")
        self.res.config(state="disabled")

        # препоръка
        self.rec.config(state="normal")
        self.rec.insert("end", "Окончателна препоръка\n\n", "h")
        self.rec.insert("end", result.recommendation + "\n\n", "body")
        comp = result.finding_by(AgentRole.COMPLIANCE)
        if comp:
            self.rec.insert("end", f"Съответствие: {comp.summary}\n", "body")
        self.rec.config(state="disabled")

        self._set_status(f"Готово — {result.rounds} кръга, "
                         f"{len(result.critiques)} възражения.")
        self.nb.select(4)

    def _export(self) -> None:
        if not self.result:
            messagebox.showinfo("Няма резултат", "Първо стартирайте консултация.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt", title="Запазване на отчета",
            filetypes=[("Текстов файл", "*.txt")])
        if not path:
            return
        r = self.result
        lines = [f"PROVENIRE — отчет от консултация", f"Въпрос: {r.question}",
                 f"Кръгове: {r.rounds}", "", "ДНЕВНИК", "-" * 60]
        lines += [m.short() for m in r.transcript]
        lines += ["", "ВЪЗРАЖЕНИЯ", "-" * 60] + [str(c) for c in r.critiques]
        lines += ["", "ПРЕПОРЪКА", "-" * 60, r.recommendation]
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
        self._set_status(f"Отчетът е записан: {path}")


def main() -> None:
    app = ProvenireApp()
    app.mainloop()


if __name__ == "__main__":
    main()
