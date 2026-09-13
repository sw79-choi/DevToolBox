# -*- coding: utf-8 -*-
"""The shell. It arranges category tabs and tool tabs from plugin metadata alone."""
from __future__ import annotations

import logging
import traceback
from collections import OrderedDict
from typing import Dict, List

from ..core import paths
from ..core.app_settings import APP_NS
from ..core.context import AppContext
from ..core.logging_setup import set_console_level
from ..core.qt import QByteArray, TEXT_SELECTABLE, QtWidgets
from ..core.registry import LoadError
from .settings_dialog import open_settings
from .theme import apply_theme

log = logging.getLogger(__name__)

ERROR_CATEGORY = "Problems"


class _ErrorPage(QtWidgets.QWidget):
    """Shown in place of a tool that could not be loaded or built."""

    def __init__(self, title: str, detail: str, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        heading = QtWidgets.QLabel("<b>%s</b>" % title)
        heading.setTextInteractionFlags(TEXT_SELECTABLE)
        heading.setWordWrap(True)
        layout.addWidget(heading)
        view = QtWidgets.QPlainTextEdit(detail)
        view.setReadOnly(True)
        layout.addWidget(view, 1)
        open_logs = QtWidgets.QPushButton("Open Log Folder")
        open_logs.clicked.connect(lambda: paths.open_in_file_manager(paths.log_dir()))
        row = QtWidgets.QHBoxLayout()
        row.addStretch(1)
        row.addWidget(open_logs)
        layout.addLayout(row)


class ToolHost(QtWidgets.QWidget):
    """Wrapper for one tool tab. The real widget is built the first time it shows."""

    def __init__(self, plugin, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.plugin = plugin
        self.ctx = ctx
        self.inner = None
        self._built = False
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

    @property
    def built(self) -> bool:
        return self._built

    def showEvent(self, event):
        if not self._built:
            self._built = True
            self._build()
        super().showEvent(event)

    def _build(self):
        try:
            self.inner = self.plugin.create_widget(self.ctx)
        except Exception as exc:
            log.exception("Could not build tool widget: %s", self.plugin.meta.id)
            self.inner = _ErrorPage(
                "%s could not be opened: %s" % (self.plugin.meta.title, exc),
                traceback.format_exc(),
            )
        self.layout().addWidget(self.inner)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, manager, plugins, errors: List[LoadError], tasks, app=None):
        super().__init__()
        self.setWindowTitle("DevToolBox")
        self.resize(1020, 700)
        self._manager = manager
        self._app = app
        self._plugins = plugins
        self._tasks = tasks
        self._hosts: Dict[str, ToolHost] = {}
        self._contexts: Dict[str, AppContext] = {}
        self._app_cfg = manager.scope(APP_NS)

        self.tabs = QtWidgets.QTabWidget()      # outer tabs are categories
        self.tabs.setDocumentMode(True)
        self.setCentralWidget(self.tabs)

        self._build_tabs(plugins, errors)
        self._build_menus()
        self._build_statusbar(len(plugins), len(errors))

        manager.changed.connect(self._on_config_changed)
        self._restore_window_state()

    # -------------------------------------------------------------------- tabs
    def _context_for(self, plugin) -> AppContext:
        ctx = AppContext(
            config=self._manager.scope("tools.%s" % plugin.meta.id),
            app_config=self._app_cfg,
            tasks=self._tasks,
            log=logging.getLogger("devtoolbox.tools.%s" % plugin.meta.id),
            notify=self.notify,
            main_window=self,
        )
        self._contexts[plugin.meta.id] = ctx
        return ctx

    def _build_tabs(self, plugins, errors):
        # The registry sorted by order, so first appearance sets category order.
        grouped: "OrderedDict[str, list]" = OrderedDict()
        for plugin in plugins:
            grouped.setdefault(plugin.meta.category, []).append(plugin)

        for category, tools in grouped.items():
            if len(tools) == 1:
                # A single tool needs no inner tab bar.
                plugin = tools[0]
                page = ToolHost(plugin, self._context_for(plugin))
                page.setToolTip(plugin.meta.description)
                self._hosts[plugin.meta.id] = page
            else:
                page = QtWidgets.QTabWidget()
                page.setDocumentMode(True)
                for plugin in tools:
                    host = ToolHost(plugin, self._context_for(plugin))
                    self._hosts[plugin.meta.id] = host
                    index = page.addTab(host, plugin.meta.title)
                    page.setTabToolTip(index, plugin.meta.description)
                page.currentChanged.connect(self._remember_tab)
            self.tabs.addTab(page, category)

        if errors:
            detail = "\n\n".join("[%s] %s\n%s" % (e.module, e.message, e.traceback)
                                 for e in errors)
            self.tabs.addTab(
                _ErrorPage("%d tool(s) failed to load" % len(errors), detail),
                ERROR_CATEGORY)

        if not plugins and not errors:
            self.tabs.addTab(
                _ErrorPage(
                    "No tools registered",
                    "Create a folder under devtoolbox/tools/ and put\n"
                    "    TOOL = MyTool()\n"
                    "in its __init__.py. A tab appears on the next start."),
                "Start")

        self.tabs.currentChanged.connect(self._remember_tab)

    def _current_tool_id(self):
        page = self.tabs.currentWidget()
        if isinstance(page, ToolHost):
            return page.plugin.meta.id
        if isinstance(page, QtWidgets.QTabWidget):
            inner = page.currentWidget()
            if isinstance(inner, ToolHost):
                return inner.plugin.meta.id
        return None

    def _remember_tab(self, *_):
        tool_id = self._current_tool_id()
        if tool_id:
            self._app_cfg.set("last_tab", tool_id)

    def _select_tool(self, tool_id: str) -> bool:
        for i in range(self.tabs.count()):
            page = self.tabs.widget(i)
            if isinstance(page, ToolHost) and page.plugin.meta.id == tool_id:
                self.tabs.setCurrentIndex(i)
                return True
            if isinstance(page, QtWidgets.QTabWidget):
                for j in range(page.count()):
                    inner = page.widget(j)
                    if isinstance(inner, ToolHost) and inner.plugin.meta.id == tool_id:
                        self.tabs.setCurrentIndex(i)
                        page.setCurrentIndex(j)
                        return True
        return False

    # ------------------------------------------------------------------- menus
    def _build_menus(self):
        bar = self.menuBar()

        file_menu = bar.addMenu("&File")
        settings_action = file_menu.addAction("Settings...")
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self.open_settings)
        file_menu.addSeparator()
        quit_action = file_menu.addAction("Quit")
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)

        tools_menu = bar.addMenu("&Tools")
        tools_menu.addAction("Open Config Folder").triggered.connect(
            lambda: paths.open_in_file_manager(self._manager.path))
        tools_menu.addAction("Open Log Folder").triggered.connect(
            lambda: paths.open_in_file_manager(paths.log_dir()))
        tools_menu.addSeparator()
        tools_menu.addAction("Export Settings...").triggered.connect(self._export_config)
        tools_menu.addAction("Import Settings...").triggered.connect(self._import_config)

        help_menu = bar.addMenu("&Help")
        help_menu.addAction("About").triggered.connect(self._about)

    def open_settings(self):
        open_settings(self._manager, self._plugins, self._contexts, self)

    def _export_config(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export Settings", "devtoolbox-config.json", "JSON (*.json)")
        if path:
            self._manager.save_now()
            self._manager.export_to(path)
            self.notify("Settings exported to %s" % path)

    def _import_config(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Import Settings", "", "JSON (*.json)")
        if not path:
            return
        try:
            self._manager.import_from(path)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(
                self, "DevToolBox", "Could not import that file:\n%s" % exc)
            return
        QtWidgets.QMessageBox.information(
            self, "DevToolBox",
            "Settings imported. Some of them apply after a restart.")

    def _about(self):
        from ..core.qt import QT_API
        QtWidgets.QMessageBox.about(
            self, "DevToolBox",
            "<b>DevToolBox</b><br><br>"
            "One tab per tool, one config.json for every setting.<br><br>"
            "Qt binding: %s<br>Config file: %s<br>Portable mode: %s"
            % (QT_API, self._manager.path, "yes" if paths.is_portable() else "no"))

    # -------------------------------------------------------------- status bar
    def _build_statusbar(self, tool_count, error_count):
        self._status_label = QtWidgets.QLabel()
        text = "%d tool(s)" % tool_count
        if error_count:
            text += "  |  %d failed to load" % error_count
        self._status_label.setText(text)
        self.statusBar().addPermanentWidget(self._status_label)
        self.notify("Ready")

    def notify(self, message: str, msec: int = 5000) -> None:
        self.statusBar().showMessage(message, msec)

    # ------------------------------------------------------- react to settings
    def _on_config_changed(self, path, _value):
        if path in ("", "app.theme") and self._app:
            apply_theme(self._app, self._app_cfg.get("theme", "system"))
        if path in ("", "app.log_level"):
            set_console_level(self._app_cfg.get("log_level", "INFO"))

    # ------------------------------------------------------ window state / exit
    def _restore_window_state(self):
        geometry = self._manager.get("window.geometry")
        if geometry:
            try:
                self.restoreGeometry(QByteArray.fromBase64(geometry.encode("ascii")))
            except Exception:
                log.debug("Could not restore window geometry", exc_info=True)
        if self._app_cfg.get("restore_last_tab", True):
            last_tab = self._app_cfg.get("last_tab")
            if last_tab:
                self._select_tool(last_tab)

    def closeEvent(self, event):
        for tool_id, host in self._hosts.items():
            if not host.built:
                continue          # never opened, nothing to ask about
            try:
                if not host.plugin.on_close():
                    event.ignore()
                    self.notify("%s still has work in progress."
                                % host.plugin.meta.title)
                    return
            except Exception:
                log.exception("on_close failed for %s", tool_id)

        try:
            self._manager.set(
                "window.geometry",
                bytes(self.saveGeometry().toBase64()).decode("ascii"))
        except Exception:
            log.exception("Could not save window geometry")
        self._manager.save_now()
        super().closeEvent(event)
