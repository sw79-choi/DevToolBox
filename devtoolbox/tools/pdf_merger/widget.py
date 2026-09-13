# -*- coding: utf-8 -*-
"""PDF Merger screen. All state lives in ctx.config; all work goes to ctx.tasks."""
from __future__ import annotations

import os

from ...core.qt import ROLE_USER, QtGui, QtWidgets
from ...ui.widgets.file_drop_list import FileDropList
from .logic import MergeOptions, merge_pdfs, natural_key, read_page_count

ODD_COLOR = "#b9770e"
ERROR_COLOR = "#c0392b"


class _Entry:
    """One row of the list: a path plus what we know about it."""

    def __init__(self, path: str):
        self.path = os.path.abspath(path)
        self.name = os.path.basename(self.path)
        self.pages = None
        self.error = None
        try:
            self.pages = read_page_count(self.path)
        except Exception as exc:
            self.error = str(exc) or exc.__class__.__name__

    @property
    def is_odd(self) -> bool:
        return self.pages is not None and self.pages % 2 == 1

    def label(self, pad_enabled: bool) -> str:
        if self.error:
            return "%s    could not be read: %s" % (self.name, self.error)
        suffix = ""
        if self.is_odd:
            suffix = "    odd - blank page added" if pad_enabled else "    odd"
        return "%s    (%d pages)%s" % (self.name, self.pages, suffix)


class PdfMergerWidget(QtWidgets.QWidget):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.cfg = ctx.config
        self.entries = []
        self.handle = None
        self._build_ui()
        self.cfg.changed.connect(self._on_setting_changed)

    # ---------------------------------------------------------------- layout
    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        hint = QtWidgets.QLabel(
            "Drop PDF files or folders below. Drag rows to change the print order.")
        hint.setStyleSheet("color: palette(mid);")
        root.addWidget(hint)

        middle = QtWidgets.QHBoxLayout()
        self.list = FileDropList(extensions=(".pdf",))
        self.list.filesDropped.connect(self.add_paths)
        self.list.model().rowsMoved.connect(self._rows_moved)
        middle.addWidget(self.list, 1)

        side = QtWidgets.QVBoxLayout()
        side.setSpacing(6)

        def button(text, slot, tooltip=""):
            widget = QtWidgets.QPushButton(text)
            widget.clicked.connect(slot)
            widget.setMinimumWidth(130)
            if tooltip:
                widget.setToolTip(tooltip)
            side.addWidget(widget)
            return widget

        button("Add Files...", self.on_add_files)
        button("Add Folder...", self.on_add_folder,
               "Adds every PDF in the folder")
        side.addSpacing(8)
        button("Move Up", lambda: self.move_selected(-1))
        button("Move Down", lambda: self.move_selected(1))
        button("Sort by Name", self.sort_by_name)
        side.addSpacing(8)
        button("Remove", self.remove_selected)
        button("Clear", self.clear_all)
        side.addStretch(1)
        middle.addLayout(side)
        root.addLayout(middle)

        # The duplex option is mirrored here and in Settings; both write config.
        options = QtWidgets.QHBoxLayout()
        self.pad_check = QtWidgets.QCheckBox(
            "Add a blank page after odd-length documents (for duplex printing)")
        self.pad_check.setChecked(bool(self.cfg.get("pad_odd")))
        self.pad_check.toggled.connect(lambda v: self.cfg.set("pad_odd", v))
        options.addWidget(self.pad_check)
        options.addStretch(1)
        root.addLayout(options)

        output_row = QtWidgets.QHBoxLayout()
        output_row.addWidget(QtWidgets.QLabel("Save to:"))
        self.output_edit = QtWidgets.QLineEdit()
        self.output_edit.setPlaceholderText("Choose where the merged PDF goes")
        output_row.addWidget(self.output_edit, 1)
        browse = QtWidgets.QPushButton("Browse...")
        browse.clicked.connect(self.on_pick_output)
        output_row.addWidget(browse)
        root.addLayout(output_row)

        bottom = QtWidgets.QHBoxLayout()
        self.progress = QtWidgets.QProgressBar()
        bottom.addWidget(self.progress, 1)
        self.merge_button = QtWidgets.QPushButton("Merge")
        self.merge_button.setMinimumSize(140, 34)
        font = self.merge_button.font()
        font.setBold(True)
        self.merge_button.setFont(font)
        self.merge_button.clicked.connect(self.on_merge)
        bottom.addWidget(self.merge_button)
        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.on_cancel)
        bottom.addWidget(self.cancel_button)
        root.addLayout(bottom)

        self.summary = QtWidgets.QLabel()
        self.summary.setStyleSheet("color: palette(mid);")
        root.addWidget(self.summary)
        self._refresh()

    # ------------------------------------------------------------ list edits
    def _on_setting_changed(self, key, _value):
        if key in ("pad_odd", ""):
            self.pad_check.blockSignals(True)
            self.pad_check.setChecked(bool(self.cfg.get("pad_odd")))
            self.pad_check.blockSignals(False)
            self._refresh()

    def _rows_moved(self, *_):
        """Keep self.entries in step after a drag reorder."""
        by_path = {entry.path: entry for entry in self.entries}
        reordered = []
        for row in range(self.list.count()):
            path = self.list.item(row).data(ROLE_USER)
            if path in by_path:
                reordered.append(by_path[path])
        if len(reordered) == len(self.entries):
            self.entries = reordered
        self._refresh()

    def add_paths(self, paths):
        files = []
        for path in paths:
            if os.path.isdir(path):
                files.extend(self._scan_folder(path))
            elif path.lower().endswith(".pdf"):
                files.append(path)
        self._add_files(files)

    def _scan_folder(self, folder):
        found = []
        if self.cfg.get("recursive"):
            for root_dir, _dirs, names in os.walk(folder):
                found += [os.path.join(root_dir, n) for n in names
                          if n.lower().endswith(".pdf")]
        else:
            found = [os.path.join(folder, n) for n in os.listdir(folder)
                     if n.lower().endswith(".pdf")
                     and os.path.isfile(os.path.join(folder, n))]
        found.sort(key=lambda p: natural_key(os.path.basename(p)))
        return found

    def _add_files(self, files):
        known = {entry.path for entry in self.entries}
        added = duplicates = 0
        for path in files:
            absolute = os.path.abspath(path)
            if absolute in known:
                duplicates += 1
                continue
            entry = _Entry(absolute)
            self.entries.append(entry)
            known.add(absolute)
            item = QtWidgets.QListWidgetItem("")
            item.setData(ROLE_USER, absolute)
            item.setToolTip(absolute)
            self.list.addItem(item)
            added += 1
        self._refresh()
        note = "Added %d file(s)" % added
        if duplicates:
            note += ", skipped %d already in the list" % duplicates
        self.ctx.notify(note)

    def on_add_files(self):
        start = self.cfg.get("last_dir") or ""
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self, "Select PDF files", start, "PDF files (*.pdf);;All files (*.*)")
        if files:
            self.cfg.set("last_dir", os.path.dirname(files[0]))
            files.sort(key=lambda p: natural_key(os.path.basename(p)))
            self._add_files(files)
            self._suggest_output(os.path.dirname(files[0]))

    def on_add_folder(self):
        start = self.cfg.get("last_dir") or ""
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select a folder of PDFs", start)
        if folder:
            self.cfg.set("last_dir", folder)
            self._add_files(self._scan_folder(folder))
            self._suggest_output(folder, os.path.basename(folder.rstrip("/\\")))

    def _suggest_output(self, folder, base=None):
        if self.output_edit.text().strip():
            return
        self.output_edit.setText(os.path.join(folder, "%s_merged.pdf" % (base or "documents")))

    def remove_selected(self):
        for row in self.list.selected_rows():
            self.list.takeItem(row)
            del self.entries[row]
        self._refresh()

    def clear_all(self):
        self.list.clear()
        self.entries = []
        self._refresh()

    def move_selected(self, delta):
        rows = self.list.selected_rows(descending=delta > 0)
        for row in rows:
            target = row + delta
            if target < 0 or target >= self.list.count():
                continue
            item = self.list.takeItem(row)
            self.list.insertItem(target, item)
            item.setSelected(True)
            self.entries.insert(target, self.entries.pop(row))
        self._refresh()

    def sort_by_name(self):
        self.entries.sort(key=lambda e: natural_key(e.name))
        self.list.clear()
        for entry in self.entries:
            item = QtWidgets.QListWidgetItem("")
            item.setData(ROLE_USER, entry.path)
            item.setToolTip(entry.path)
            self.list.addItem(item)
        self._refresh()

    def _refresh(self):
        pad = bool(self.cfg.get("pad_odd"))
        content = blanks = errors = 0
        for row, entry in enumerate(self.entries):
            if row >= self.list.count():
                break
            item = self.list.item(row)
            item.setText("%3d.  %s" % (row + 1, entry.label(pad)))
            if entry.error:
                item.setForeground(QtGui.QBrush(QtGui.QColor(ERROR_COLOR)))
                errors += 1
            elif entry.is_odd:
                item.setForeground(QtGui.QBrush(QtGui.QColor(ODD_COLOR)))
                content += entry.pages
                if pad:
                    blanks += 1
            else:
                item.setForeground(QtGui.QBrush())
                content += entry.pages

        summary = "%d document(s), %d content page(s)" % (
            len(self.entries) - errors, content)
        if pad and blanks:
            summary += ", %d blank page(s) -> %d total" % (blanks, content + blanks)
        else:
            summary += ", %d total" % content
        if errors:
            summary += "  |  %d unreadable" % errors
        self.summary.setText(summary)

    # ----------------------------------------------------------------- merge
    def on_pick_output(self):
        start = self.output_edit.text().strip() or self.cfg.get("last_dir") or ""
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save merged PDF", start, "PDF files (*.pdf)")
        if path:
            if not path.lower().endswith(".pdf"):
                path += ".pdf"
            self.output_edit.setText(path)

    def on_merge(self):
        usable = [entry for entry in self.entries if not entry.error]
        if not usable:
            QtWidgets.QMessageBox.warning(
                self, "PDF Merger", "Add at least one readable PDF first.")
            return

        output = self.output_edit.text().strip()
        if not output:
            self.on_pick_output()
            output = self.output_edit.text().strip()
            if not output:
                return
        if not output.lower().endswith(".pdf"):
            output += ".pdf"
            self.output_edit.setText(output)
        output = os.path.abspath(output)

        if any(output == entry.path for entry in self.entries):
            QtWidgets.QMessageBox.warning(
                self, "PDF Merger",
                "The output path is one of the source files. Pick another name.")
            return
        if os.path.exists(output):
            from ...core.qt import MB_NO, MB_YES
            answer = QtWidgets.QMessageBox.question(
                self, "PDF Merger",
                "That file already exists. Overwrite it?\n\n%s" % output,
                MB_YES | MB_NO)
            if answer != MB_YES:
                return
        folder = os.path.dirname(output)
        if folder and not os.path.isdir(folder):
            try:
                os.makedirs(folder, exist_ok=True)
            except OSError as exc:
                QtWidgets.QMessageBox.critical(
                    self, "PDF Merger", "Could not create that folder:\n%s" % exc)
                return

        options = MergeOptions(
            pad_odd=bool(self.cfg.get("pad_odd")),
            pad_size=self.cfg.get("pad_size") or "last",
            bookmarks=bool(self.cfg.get("bookmarks")),
        )
        self._set_busy(True)
        self.handle = self.ctx.tasks.submit(
            merge_pdfs, [entry.path for entry in usable], output, options,
            on_progress=self.progress.setValue,
            on_message=self.ctx.notify,
            on_done=self._on_done,
            on_error=self._on_error,
        )

    def on_cancel(self):
        if self.handle:
            self.handle.cancel()
            self.ctx.notify("Cancelling...")

    def _set_busy(self, busy):
        self.merge_button.setEnabled(not busy)
        self.merge_button.setText("Merging..." if busy else "Merge")
        self.cancel_button.setEnabled(busy)
        self.list.setEnabled(not busy)
        if not busy:
            self.progress.setValue(0)

    def _on_done(self, result):
        self._set_busy(False)
        if result.cancelled:
            self.ctx.notify("Merge cancelled")
            return
        lines = [
            "Merged %d document(s), %d content page(s)."
            % (result.files, result.content_pages),
        ]
        if result.blank_pages:
            lines.append("Added %d blank page(s) so each document starts on a front side."
                         % result.blank_pages)
        lines.append("Result: %d pages" % result.total_pages)
        lines.append("")
        lines.append(result.output_path)
        if result.skipped:
            lines.append("")
            lines.append("Skipped:")
            lines += [" - %s (%s)" % (name, why) for name, why in result.skipped[:10]]
        QtWidgets.QMessageBox.information(self, "PDF Merger", "\n".join(lines))
        self.ctx.notify("Saved %s" % result.output_path)
        if self.cfg.get("open_when_done"):
            from ...core import paths as core_paths
            core_paths.open_in_file_manager(result.output_path)

    def _on_error(self, detail):
        self._set_busy(False)
        QtWidgets.QMessageBox.critical(self, "PDF Merger", "Merge failed.\n\n%s" % detail)
        self.ctx.notify("Merge failed")

    def is_busy(self) -> bool:
        return bool(self.handle and not self.handle.finished)
