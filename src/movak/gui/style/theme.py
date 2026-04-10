from __future__ import annotations

from pathlib import Path

import pyqtgraph as pg
from PyQt6.QtWidgets import QApplication

from .fonts import load_fonts
from .palette import Palette
from .spacing import FontSize, Radius, Spacing


def _theme_tokens() -> dict[str, str | int]:
    return {
        "window": Palette.WINDOW,
        "background": Palette.BACKGROUND,
        "frame": Palette.FRAME,
        "panel": Palette.PANEL,
        "surface_0": Palette.SURFACE_0,
        "surface_1": Palette.SURFACE_1,
        "surface_2": Palette.SURFACE_2,
        "surface_3": Palette.SURFACE_3,
        "surface_elevated": Palette.SURFACE_ELEVATED,
        "border": Palette.BORDER,
        "border_strong": Palette.BORDER_STRONG,
        "separator": Palette.SEPARATOR,
        "text": Palette.TEXT,
        "text_muted": Palette.TEXT_MUTED,
        "text_dim": Palette.TEXT_DIM,
        "text_on_accent": Palette.TEXT_ON_ACCENT,
        "accent": Palette.ACCENT,
        "accent_hover": Palette.ACCENT_HOVER,
        "accent_strong": Palette.ACCENT_STRONG,
        "accent_violet": Palette.ACCENT_VIOLET,
        "accent_violet_soft": Palette.ACCENT_VIOLET_SOFT,
        "success": Palette.SUCCESS,
        "warning": Palette.WARNING,
        "error": Palette.ERROR,
        "cursor": Palette.CURSOR,
        "waveform": Palette.WAVEFORM,
        "waveform_fill": Palette.WAVEFORM_FILL,
        "panel_glow": Palette.PANEL_GLOW,
        "radius_sm": Radius.SM,
        "radius_md": Radius.MD,
        "radius_lg": Radius.LG,
        "radius_xl": Radius.XL,
        "space_xxs": Spacing.XXS,
        "space_xs": Spacing.XS,
        "space_s": Spacing.S,
        "space_sm": Spacing.SM,
        "space_ms": Spacing.MS,
        "space_md": Spacing.MD,
        "space_lg": Spacing.LG,
        "space_xl": Spacing.XL,
        "space_xxl": Spacing.XXL,
        "font_xs": FontSize.XS,
        "font_sm": FontSize.SM,
        "font_md": FontSize.MD,
        "font_lg": FontSize.LG,
        "font_xl": FontSize.XL,
        "font_xxl": FontSize.XXL,
    }


def apply_theme(app: QApplication) -> None:
    """Apply the Movak dark theme and global plotting defaults."""

    load_fonts()
    app.setStyle("Fusion")

    qss_path = Path(__file__).with_name("movak_dark.qss")
    stylesheet = qss_path.read_text(encoding="utf-8").format(**_theme_tokens())
    app.setStyleSheet(stylesheet)

    pg.setConfigOption("background", Palette.SURFACE_1)
    pg.setConfigOption("foreground", Palette.TEXT)
    pg.setConfigOptions(antialias=True)
