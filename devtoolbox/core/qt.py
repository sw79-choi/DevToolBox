# -*- coding: utf-8 -*-
"""The only module that imports PyQt directly.

Every other module must reach Qt through `from ..core.qt import ...`.
Enum path differences between PyQt6 and PyQt5 are absorbed here, so swapping
the binding later touches exactly one file.
"""
from __future__ import annotations

QT_API = ""
try:
    from PyQt6 import QtCore, QtGui, QtWidgets
    from PyQt6.QtCore import Qt
    from PyQt6.QtCore import pyqtSignal as Signal, pyqtSlot as Slot
    QT_API = "PyQt6"
except ImportError:
    try:
        from PyQt5 import QtCore, QtGui, QtWidgets
        from PyQt5.QtCore import Qt
        from PyQt5.QtCore import pyqtSignal as Signal, pyqtSlot as Slot
        QT_API = "PyQt5"
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "PyQt6 or PyQt5 is required.  pip install PyQt6"
        ) from exc

QObject = QtCore.QObject
QTimer = QtCore.QTimer
QThreadPool = QtCore.QThreadPool
QRunnable = QtCore.QRunnable
QByteArray = QtCore.QByteArray
QSize = QtCore.QSize

if QT_API == "PyQt6":
    ALIGN_CENTER = Qt.AlignmentFlag.AlignCenter
    ALIGN_LEFT = Qt.AlignmentFlag.AlignLeft
    ALIGN_RIGHT = Qt.AlignmentFlag.AlignRight
    ALIGN_TOP = Qt.AlignmentFlag.AlignTop
    ALIGN_VCENTER = Qt.AlignmentFlag.AlignVCenter
    ROLE_USER = Qt.ItemDataRole.UserRole
    WAIT_CURSOR = Qt.CursorShape.WaitCursor
    ORIENT_H = Qt.Orientation.Horizontal
    ORIENT_V = Qt.Orientation.Vertical
    TEXT_SELECTABLE = Qt.TextInteractionFlag.TextSelectableByMouse
    DND_INTERNAL_MOVE = QtWidgets.QAbstractItemView.DragDropMode.InternalMove
    SEL_EXTENDED = QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection
    MB_YES = QtWidgets.QMessageBox.StandardButton.Yes
    MB_NO = QtWidgets.QMessageBox.StandardButton.No
    DBB_OK = QtWidgets.QDialogButtonBox.StandardButton.Ok
    DBB_CANCEL = QtWidgets.QDialogButtonBox.StandardButton.Cancel
    DBB_RESET = QtWidgets.QDialogButtonBox.StandardButton.RestoreDefaults
    DIALOG_ACCEPTED = QtWidgets.QDialog.DialogCode.Accepted
    FRAME_HLINE = QtWidgets.QFrame.Shape.HLine
    FRAME_SUNKEN = QtWidgets.QFrame.Shadow.Sunken
    SP_EXPANDING = QtWidgets.QSizePolicy.Policy.Expanding
    COLOR_WINDOW = QtGui.QPalette.ColorRole.Window
    COLOR_WINDOW_TEXT = QtGui.QPalette.ColorRole.WindowText
    COLOR_BASE = QtGui.QPalette.ColorRole.Base
    COLOR_ALT_BASE = QtGui.QPalette.ColorRole.AlternateBase
    COLOR_TEXT = QtGui.QPalette.ColorRole.Text
    COLOR_BUTTON = QtGui.QPalette.ColorRole.Button
    COLOR_BUTTON_TEXT = QtGui.QPalette.ColorRole.ButtonText
    COLOR_HIGHLIGHT = QtGui.QPalette.ColorRole.Highlight
    COLOR_HIGHLIGHT_TEXT = QtGui.QPalette.ColorRole.HighlightedText
    COLOR_TOOLTIP_BASE = QtGui.QPalette.ColorRole.ToolTipBase
    COLOR_TOOLTIP_TEXT = QtGui.QPalette.ColorRole.ToolTipText

    def exec_(obj):
        """Run a QDialog / QApplication (PyQt5 spells this exec_)."""
        return obj.exec()
else:  # PyQt5
    ALIGN_CENTER = Qt.AlignCenter
    ALIGN_LEFT = Qt.AlignLeft
    ALIGN_RIGHT = Qt.AlignRight
    ALIGN_TOP = Qt.AlignTop
    ALIGN_VCENTER = Qt.AlignVCenter
    ROLE_USER = Qt.UserRole
    WAIT_CURSOR = Qt.WaitCursor
    ORIENT_H = Qt.Horizontal
    ORIENT_V = Qt.Vertical
    TEXT_SELECTABLE = Qt.TextSelectableByMouse
    DND_INTERNAL_MOVE = QtWidgets.QAbstractItemView.InternalMove
    SEL_EXTENDED = QtWidgets.QAbstractItemView.ExtendedSelection
    MB_YES = QtWidgets.QMessageBox.Yes
    MB_NO = QtWidgets.QMessageBox.No
    DBB_OK = QtWidgets.QDialogButtonBox.Ok
    DBB_CANCEL = QtWidgets.QDialogButtonBox.Cancel
    DBB_RESET = QtWidgets.QDialogButtonBox.RestoreDefaults
    DIALOG_ACCEPTED = QtWidgets.QDialog.Accepted
    FRAME_HLINE = QtWidgets.QFrame.HLine
    FRAME_SUNKEN = QtWidgets.QFrame.Sunken
    SP_EXPANDING = QtWidgets.QSizePolicy.Expanding
    COLOR_WINDOW = QtGui.QPalette.Window
    COLOR_WINDOW_TEXT = QtGui.QPalette.WindowText
    COLOR_BASE = QtGui.QPalette.Base
    COLOR_ALT_BASE = QtGui.QPalette.AlternateBase
    COLOR_TEXT = QtGui.QPalette.Text
    COLOR_BUTTON = QtGui.QPalette.Button
    COLOR_BUTTON_TEXT = QtGui.QPalette.ButtonText
    COLOR_HIGHLIGHT = QtGui.QPalette.Highlight
    COLOR_HIGHLIGHT_TEXT = QtGui.QPalette.HighlightedText
    COLOR_TOOLTIP_BASE = QtGui.QPalette.ToolTipBase
    COLOR_TOOLTIP_TEXT = QtGui.QPalette.ToolTipText

    def exec_(obj):
        return obj.exec_()
