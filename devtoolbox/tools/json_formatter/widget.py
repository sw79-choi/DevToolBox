# -*- coding: utf-8 -*-
from __future__ import annotations

from ...core.qt import ORIENT_H, QtGui, QtWidgets
from .logic import format_json, minify_json, validate

SAMPLE = '{"name":"DevToolBox","tools":["pdf_merger","hash"],"version":1}'


class JsonFormatterWidget(QtWidgets.QWidget):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.cfg = ctx.config
        self._build_ui()

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        mono = QtGui.QFontDatabase.systemFont(
            QtGui.QFontDatabase.SystemFont.FixedFont
            if hasattr(QtGui.QFontDatabase, "SystemFont")
            else QtGui.QFontDatabase.FixedFont)

        splitter = QtWidgets.QSplitter(ORIENT_H)
        self.input = QtWidgets.QPlainTextEdit()
        self.input.setFont(mono)
        self.input.setPlaceholderText("Paste JSON here")
        self.input.setPlainText(SAMPLE)          # opens in a working state
        self.output = QtWidgets.QPlainTextEdit()
        self.output.setFont(mono)
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("Result")
        splitter.addWidget(self.input)
        splitter.addWidget(self.output)
        splitter.setSizes([420, 420])
        root.addWidget(splitter, 1)

        row = QtWidgets.QHBoxLayout()
        for text, slot in (("Format", self.on_format),
                           ("Minify", self.on_minify),
                           ("Validate", self.on_validate)):
            button = QtWidgets.QPushButton(text)
            button.clicked.connect(slot)
            row.addWidget(button)
        row.addStretch(1)
        copy_button = QtWidgets.QPushButton("Copy Result")
        copy_button.clicked.connect(self.on_copy)
        row.addWidget(copy_button)
        clear_button = QtWidgets.QPushButton("Clear")
        clear_button.clicked.connect(lambda: (self.input.clear(), self.output.clear()))
        row.addWidget(clear_button)
        root.addLayout(row)

        self.status = QtWidgets.QLabel("Ready")
        self.status.setStyleSheet("color: palette(mid);")
        root.addWidget(self.status)

    def _run(self, fn):
        try:
            result = fn(self.input.toPlainText())
        except Exception as exc:
            self.output.setPlainText("")
            self.status.setText("Error: %s" % exc)
            self.ctx.notify("JSON error: %s" % exc)
            return
        self.output.setPlainText(result)
        self.status.setText("Done - %d characters" % len(result))

    def on_format(self):
        self._run(lambda text: format_json(
            text,
            indent=int(self.cfg.get("indent") or 2),
            sort_keys=bool(self.cfg.get("sort_keys")),
            ensure_ascii=bool(self.cfg.get("ensure_ascii")),
        ))

    def on_minify(self):
        self._run(lambda text: minify_json(
            text,
            sort_keys=bool(self.cfg.get("sort_keys")),
            ensure_ascii=bool(self.cfg.get("ensure_ascii")),
        ))

    def on_validate(self):
        ok, message = validate(self.input.toPlainText())
        self.status.setText(message)
        self.ctx.notify(message)

    def on_copy(self):
        QtWidgets.QApplication.clipboard().setText(self.output.toPlainText())
        self.ctx.notify("Result copied to the clipboard")
