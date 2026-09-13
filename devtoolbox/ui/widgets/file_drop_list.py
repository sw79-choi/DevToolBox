# -*- coding: utf-8 -*-
"""Shared file list widget: drag and drop in, drag to reorder."""
from __future__ import annotations

import os
from typing import List

from ...core.qt import DND_INTERNAL_MOVE, ROLE_USER, SEL_EXTENDED, QtWidgets, Signal


class FileDropList(QtWidgets.QListWidget):
    """Holds paths. Emits filesDropped when files or folders are dropped on it."""

    filesDropped = Signal(list)

    def __init__(self, extensions=(".pdf",), parent=None):
        super().__init__(parent)
        self._extensions = tuple(e.lower() for e in extensions)
        self.setAcceptDrops(True)
        self.setDragDropMode(DND_INTERNAL_MOVE)
        self.setSelectionMode(SEL_EXTENDED)
        self.setAlternatingRowColors(True)

    # ------------------------------------------------------------ drag & drop
    def _paths_from(self, event) -> List[str]:
        mime = event.mimeData()
        if not mime.hasUrls():
            return []
        paths = []
        for url in mime.urls():
            path = url.toLocalFile()
            if not path:
                continue
            if os.path.isdir(path) or path.lower().endswith(self._extensions):
                paths.append(path)
        return paths

    def dragEnterEvent(self, event):
        if self._paths_from(event):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if self._paths_from(event):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        paths = self._paths_from(event)
        if paths:
            event.acceptProposedAction()
            self.filesDropped.emit(paths)
        else:
            super().dropEvent(event)

    # ---------------------------------------------------------------- helpers
    def paths(self) -> List[str]:
        return [self.item(i).data(ROLE_USER) for i in range(self.count())]

    def selected_rows(self, descending: bool = True) -> List[int]:
        return sorted((self.row(i) for i in self.selectedItems()), reverse=descending)
