# -*- coding: utf-8 -*-
from __future__ import annotations

import os

from ...core.qt import QtGui, QtWidgets
from .logic import ALGORITHMS, hash_file, hash_text


class HashWidget(QtWidgets.QWidget):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.cfg = ctx.config
        self.handle = None
        self._build_ui()
        self.on_hash_text()          # show a real result immediately

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        root.addWidget(QtWidgets.QLabel("Text"))
        self.input = QtWidgets.QPlainTextEdit("DevToolBox")
        self.input.setMaximumHeight(110)
        root.addWidget(self.input)

        row = QtWidgets.QHBoxLayout()
        hash_text_button = QtWidgets.QPushButton("Hash Text")
        hash_text_button.clicked.connect(self.on_hash_text)
        row.addWidget(hash_text_button)
        hash_file_button = QtWidgets.QPushButton("Hash File...")
        hash_file_button.clicked.connect(self.on_hash_file)
        row.addWidget(hash_file_button)
        row.addStretch(1)
        root.addLayout(row)

        self.table = QtWidgets.QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Algorithm", "Digest"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
                                   if hasattr(QtWidgets.QAbstractItemView, "EditTrigger")
                                   else QtWidgets.QAbstractItemView.NoEditTriggers)
        root.addWidget(self.table, 1)

        bottom = QtWidgets.QHBoxLayout()
        self.progress = QtWidgets.QProgressBar()
        bottom.addWidget(self.progress, 1)
        copy_button = QtWidgets.QPushButton("Copy All")
        copy_button.clicked.connect(self.on_copy)
        bottom.addWidget(copy_button)
        root.addLayout(bottom)

        self.status = QtWidgets.QLabel("Ready")
        self.status.setStyleSheet("color: palette(mid);")
        root.addWidget(self.status)

    def _algorithms(self):
        chosen = self.cfg.get("algorithms") or list(ALGORITHMS)
        return [name for name in ALGORITHMS if name in chosen] or list(ALGORITHMS)

    def _show(self, digests):
        upper = bool(self.cfg.get("uppercase"))
        mono = QtGui.QFontDatabase.systemFont(
            QtGui.QFontDatabase.SystemFont.FixedFont
            if hasattr(QtGui.QFontDatabase, "SystemFont")
            else QtGui.QFontDatabase.FixedFont)
        self.table.setRowCount(len(digests))
        for row, (name, value) in enumerate(digests.items()):
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(name.upper()))
            item = QtWidgets.QTableWidgetItem(value.upper() if upper else value)
            item.setFont(mono)
            self.table.setItem(row, 1, item)
        self.table.resizeColumnToContents(0)

    def on_hash_text(self):
        digests = hash_text(self.input.toPlainText(), self._algorithms())
        self._show(digests)
        self.status.setText("Hashed %d character(s) of text"
                            % len(self.input.toPlainText()))

    def on_hash_file(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select a file", self.cfg.get("last_dir") or "")
        if not path:
            return
        self.cfg.set("last_dir", os.path.dirname(path))
        self.status.setText("Hashing %s ..." % os.path.basename(path))
        self.handle = self.ctx.tasks.submit(
            hash_file, path, self._algorithms(),
            on_progress=self.progress.setValue,
            on_done=lambda digests: self._file_done(path, digests),
            on_error=lambda detail: self.status.setText("Failed: %s" % detail),
        )

    def _file_done(self, path, digests):
        self.progress.setValue(0)
        if not digests:
            self.status.setText("Cancelled")
            return
        self._show(digests)
        size = os.path.getsize(path)
        self.status.setText("%s  (%d bytes)" % (os.path.basename(path), size))

    def on_copy(self):
        lines = []
        for row in range(self.table.rowCount()):
            lines.append("%s  %s" % (self.table.item(row, 0).text(),
                                     self.table.item(row, 1).text()))
        QtWidgets.QApplication.clipboard().setText("\n".join(lines))
        self.ctx.notify("Digests copied to the clipboard")

    def is_busy(self) -> bool:
        return bool(self.handle and not self.handle.finished)
