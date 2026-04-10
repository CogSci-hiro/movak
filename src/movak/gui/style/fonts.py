from __future__ import annotations

from pathlib import Path

from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication


def load_fonts() -> str:
    """Load bundled fonts when available and apply a modern UI font."""

    app = QApplication.instance()
    if app is None:
        return "Inter"

    font_dir = Path(__file__).with_name("assets")
    preferred_family = "Inter"

    if font_dir.exists():
        for font_path in sorted(font_dir.glob("*.ttf")):
            font_id = QFontDatabase.addApplicationFont(str(font_path))
            if font_id != -1:
                families = QFontDatabase.applicationFontFamilies(font_id)
                if families:
                    preferred_family = families[0]
                    break

    families = {family.lower() for family in QFontDatabase.families()}
    for candidate in (preferred_family, "Inter", "Segoe UI", "SF Pro Text", "Roboto", "Arial"):
        if candidate.lower() in families:
            app.setFont(QFont(candidate, 10))
            return candidate

    app.setFont(QFont(preferred_family, 10))
    return preferred_family
