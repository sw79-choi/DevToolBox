# -*- coding: utf-8 -*-
"""DevToolBox entry point. Owns the boot order and nothing else."""
from __future__ import annotations

import sys

from devtoolbox.core import logging_setup, paths
from devtoolbox.core.app_settings import APP_NS, APP_SCHEMA
from devtoolbox.core.config import ConfigManager
from devtoolbox.core.qt import QtWidgets, exec_
from devtoolbox.core.registry import discover
from devtoolbox.core.tasks import TaskRunner
from devtoolbox.ui.main_window import MainWindow
from devtoolbox.ui.theme import apply_theme


def main(argv=None) -> int:
    argv = list(sys.argv if argv is None else argv)

    # 1. Paths and logging
    paths.ensure_dirs()
    log = logging_setup.setup()

    # 2. Load settings (and migrate if the file is older)
    config = ConfigManager(paths.config_file())
    config.register_defaults(APP_NS, APP_SCHEMA)
    logging_setup.set_console_level(config.get("app.log_level", "INFO"))
    log.info("Config file: %s (portable: %s)", config.path, paths.is_portable())

    # 3. Discover plugins
    plugins, errors = discover()
    log.info("Loaded %d tool(s), %d failed", len(plugins), len(errors))

    # 4. Register tool defaults - must happen before any widget asks for a value
    for plugin in plugins:
        config.register_defaults("tools.%s" % plugin.meta.id, plugin.settings_schema())

    # 5. Application and the shared task runner
    app = QtWidgets.QApplication(argv)
    app.setApplicationName("DevToolBox")
    apply_theme(app, config.get("app.theme", "system"))
    tasks = TaskRunner(app)

    # 6-7. Build the window and restore state; tool widgets build when shown
    window = MainWindow(config, plugins, errors, tasks, app=app)
    window.show()

    # 8. Shutdown
    exit_code = exec_(app)
    config.save_now()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
