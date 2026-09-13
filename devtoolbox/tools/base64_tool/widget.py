# -*- coding: utf-8 -*-
from __future__ import annotations

from ...core.qt import ORIENT_H, QtGui, QtWidgets
from .logic import decode, encode


class Base64Widget(QtWidgets.QWidget):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.cfg = ctx.config
        self._build_ui()
        self.on_encode()

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        mono = QtGui.QFontDatabase.systemFont(
            QtGui.QFontDatabase.SystemFont.FixedFont
            if hasattr(QtGui.QFontDatabase, "SystemFont")
            else QtGui.QFontDatabase.FixedFont)

        splitter = QtWidgets.QSplitter(ORIENT_H)
        self.input = QtWidgets.QPlainTextEdit("DevToolBox")
        self.input.setFont(mono)
        self.input.setPlaceholderText("Input")
        self.output = QtWidgets.QPlainTextEdit()
        self.output.setFont(mono)
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("Result")
        splitter.addWidget(self.input)
        splitter.addWidget(self.output)
        splitter.setSizes([420, 420])
        root.addWidget(splitter, 1)

        row = QtWidgets.QHBoxLayout()
        encode_button = QtWidgets.QPushButton("Encode")
        encode_button.clicked.connect(self.on_encode)
        row.addWidget(encode_button)
        decode_button = QtWidgets.QPushButton("Decode")
        decode_button.clicked.connect(self.on_decode)
        row.addWidget(decode_button)
        swap_button = QtWidgets.QPushButton("Result to Input")
        swap_button.clicked.connect(self.on_swap)
        row.addWidget(swap_button)
        row.addStretch(1)
        copy_button = QtWidgets.QPushButton("Copy Result")
        copy_button.clicked.connect(self.on_copy)
        row.addWidget(copy_button)
        root.addLayout(row)

        self.status = QtWidgets.QLabel("Ready")
        self.status.setStyleSheet("color: palette(mid);")
        root.addWidget(self.status)

    def _run(self, fn, label):
        try:
            result = fn(self.input.toPlainText(),
                        url_safe=bool(self.cfg.get("url_safe")),
                        encoding=self.cfg.get("encoding") or "utf-8")
        except Exception as exc:
            self.output.setPlainText("")
            self.status.setText("%s failed: %s" % (label, exc))
            return
        self.output.setPlainText(result)
        self.status.setText("%s done - %d characters" % (label, len(result)))

    def on_encode(self):
        self._run(encode, "Encode")

    def on_decode(self):
        self._run(decode, "Decode")

    def on_swap(self):
        self.input.setPlainText(self.output.toPlainText())
        self.output.clear()

    def on_copy(self):
        QtWidgets.QApplication.clipboard().setText(self.output.toPlainText())
        self.ctx.notify("Result copied to the clipboard")
