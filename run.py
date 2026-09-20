"""Входна точка на приложението Provenire Agents.

Стартиране:  python run.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from provenire_agents.ui.app import main

if __name__ == "__main__":
    main()
