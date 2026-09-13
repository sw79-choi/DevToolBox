# -*- coding: utf-8 -*-
"""Application theme: the smallest proof that an app-wide setting does something."""
from __future__ import annotations

from ..core.qt import (COLOR_ALT_BASE, COLOR_BASE, COLOR_BUTTON, COLOR_BUTTON_TEXT,
                       COLOR_HIGHLIGHT, COLOR_HIGHLIGHT_TEXT, COLOR_TEXT,
                       COLOR_TOOLTIP_BASE, COLOR_TOOLTIP_TEXT, COLOR_WINDOW,
                       COLOR_WINDOW_TEXT, QtGui, QtWidgets)

_DARK_PALETTE = {
    COLOR_WINDOW: "#20242a", COLOR_WINDOW_TEXT: "#e6eaee",
    COLOR_BASE: "#191d22", COLOR_ALT_BASE: "#23282f",
    COLOR_TEXT: "#e6eaee", COLOR_BUTTON: "#2a3037", COLOR_BUTTON_TEXT: "#e6eaee",
    COLOR_HIGHLIGHT: "#3d6f9e", COLOR_HIGHLIGHT_TEXT: "#ffffff",
    COLOR_TOOLTIP_BASE: "#2a3037", COLOR_TOOLTIP_TEXT: "#e6eaee",
}


def apply_theme(app, mode: str) -> None:
    """mode is one of: system, light, dark."""
    if mode == "dark":
        app.setStyle("Fusion")
        palette = QtGui.QPalette()
        for role, color in _DARK_PALETTE.items():
            palette.setColor(role, QtGui.QColor(color))
        app.setPalette(palette)
    elif mode == "light":
        app.setStyle("Fusion")
        app.setPalette(QtWidgets.QApplication.style().standardPalette())
    else:
        app.setPalette(QtWidgets.QApplication.style().standardPalette())
