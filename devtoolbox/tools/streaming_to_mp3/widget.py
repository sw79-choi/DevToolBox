# -*- coding: utf-8 -*-
"""StreamingToMp3 screen. Records system output audio and writes an MP3."""
from __future__ import annotations

import os

from ...core.qt import MB_NO, MB_YES, QtWidgets
from .logic import format_elapsed, list_output_devices, record_to_mp3


class StreamingToMp3Widget(QtWidgets.QWidget):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.cfg = ctx.config
        self.handle = None
        self._build_ui()
        self._reload_devices()

    # ---------------------------------------------------------------- layout
    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        hint = QtWidgets.QLabel(
            "Records whatever sound the PC is currently playing (the system's output), "
            "not the microphone. Windows only.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: palette(mid);")
        root.addWidget(hint)

        device_row = QtWidgets.QHBoxLayout()
        device_row.addWidget(QtWidgets.QLabel("Output device:"))
        self.device_combo = QtWidgets.QComboBox()
        device_row.addWidget(self.device_combo, 1)
        refresh = QtWidgets.QPushButton("Refresh")
        refresh.clicked.connect(self._reload_devices)
        device_row.addWidget(refresh)
        root.addLayout(device_row)

        bitrate_row = QtWidgets.QHBoxLayout()
        bitrate_row.addWidget(QtWidgets.QLabel("Bitrate:"))
        self.bitrate_combo = QtWidgets.QComboBox()
        for kbps in (128, 192, 256, 320):
            self.bitrate_combo.addItem("%d kbps" % kbps, kbps)
        saved_bitrate = self.cfg.get("bitrate") or 192
        index = self.bitrate_combo.findData(saved_bitrate)
        self.bitrate_combo.setCurrentIndex(index if index >= 0 else 1)
        self.bitrate_combo.currentIndexChanged.connect(
            lambda _: self.cfg.set("bitrate", self.bitrate_combo.currentData()))
        bitrate_row.addWidget(self.bitrate_combo)
        bitrate_row.addStretch(1)
        root.addLayout(bitrate_row)

        output_row = QtWidgets.QHBoxLayout()
        output_row.addWidget(QtWidgets.QLabel("Save to:"))
        self.output_edit = QtWidgets.QLineEdit()
        self.output_edit.setPlaceholderText("Choose where the MP3 is written")
        output_row.addWidget(self.output_edit, 1)
        browse = QtWidgets.QPushButton("Browse...")
        browse.clicked.connect(self.on_pick_output)
        output_row.addWidget(browse)
        root.addLayout(output_row)

        bottom = QtWidgets.QHBoxLayout()
        self.record_button = QtWidgets.QPushButton("Start Recording")
        self.record_button.setMinimumSize(140, 34)
        font = self.record_button.font()
        font.setBold(True)
        self.record_button.setFont(font)
        self.record_button.clicked.connect(self.on_toggle)
        bottom.addWidget(self.record_button)
        bottom.addStretch(1)
        root.addLayout(bottom)

        self.status = QtWidgets.QLabel("Ready")
        self.status.setStyleSheet("color: palette(mid);")
        root.addWidget(self.status)
        root.addStretch(1)

    # ------------------------------------------------------------- devices
    def _reload_devices(self):
        self.device_combo.clear()
        try:
            devices = list_output_devices()
        except Exception as exc:
            self.status.setText("Could not list playback devices: %s" % exc)
            return
        for device in devices:
            self.device_combo.addItem(device["name"], device["index"])
        if devices:
            self.status.setText("%d playback device(s) found" % len(devices))
        else:
            self.status.setText("No loopback playback device found (WASAPI unavailable?)")

    # -------------------------------------------------------------- output
    def on_pick_output(self):
        start = self.output_edit.text().strip() or self.cfg.get("last_dir") or ""
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save recording", start, "MP3 files (*.mp3)")
        if path:
            if not path.lower().endswith(".mp3"):
                path += ".mp3"
            self.output_edit.setText(path)

    # ------------------------------------------------------------- record
    def on_toggle(self):
        if self.is_busy():
            self.on_stop()
        else:
            self.on_start()

    def on_start(self):
        output = self.output_edit.text().strip()
        if not output:
            self.on_pick_output()
            output = self.output_edit.text().strip()
            if not output:
                return
        if not output.lower().endswith(".mp3"):
            output += ".mp3"
            self.output_edit.setText(output)
        output = os.path.abspath(output)

        if os.path.exists(output):
            answer = QtWidgets.QMessageBox.question(
                self, "StreamingToMp3",
                "That file already exists. Overwrite it?\n\n%s" % output,
                MB_YES | MB_NO)
            if answer != MB_YES:
                return
        self.cfg.set("last_dir", os.path.dirname(output))

        device_index = self.device_combo.currentData()
        bitrate = self.bitrate_combo.currentData() or 192

        self._set_busy(True)
        self.handle = self.ctx.tasks.submit(
            record_to_mp3, output,
            device_index=device_index, bitrate=bitrate,
            on_message=self.status.setText,
            on_done=self._on_done,
            on_error=self._on_error,
        )

    def on_stop(self):
        if self.handle:
            self.handle.cancel()
            self.status.setText("Stopping...")

    def _set_busy(self, busy):
        self.record_button.setText("Stop Recording" if busy else "Start Recording")
        self.device_combo.setEnabled(not busy)
        self.bitrate_combo.setEnabled(not busy)
        self.output_edit.setEnabled(not busy)

    def _on_done(self, result):
        self._set_busy(False)
        if not result.get("frames_captured"):
            self.status.setText(
                "No audio was captured from %s - is anything playing through it?"
                % result["device_name"])
            self.ctx.notify("Recording stopped, but no audio came through")
            return
        self.status.setText(
            "Saved %s  (%s from %s)"
            % (result["output_path"], format_elapsed(result["seconds"]), result["device_name"]))
        self.ctx.notify("Recording saved to %s" % result["output_path"])
        if self.cfg.get("open_when_done"):
            from ...core import paths as core_paths
            core_paths.open_in_file_manager(result["output_path"])

    def _on_error(self, detail):
        self._set_busy(False)
        QtWidgets.QMessageBox.critical(self, "StreamingToMp3", "Recording failed.\n\n%s" % detail)
        self.ctx.notify("Recording failed")

    def is_busy(self) -> bool:
        return bool(self.handle and not self.handle.finished)
