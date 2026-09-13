# -*- coding: utf-8 -*-
"""Background task runner.

Tool code never touches Qt threads. If a worker function declares any of
`progress`, `should_cancel` or `message`, the runner injects it, which is why
logic.py can report progress and honour cancellation without importing Qt.
"""
from __future__ import annotations

import inspect
import logging
import traceback
from typing import Any, Callable, Optional

from .qt import QObject, QRunnable, QThreadPool, Signal

log = logging.getLogger(__name__)


class _TaskSignals(QObject):
    done = Signal(object)
    error = Signal(str)
    progress = Signal(int)
    message = Signal(str)


class TaskHandle:
    """Cancellation handle held by the caller."""

    def __init__(self) -> None:
        self._cancelled = False
        self._finished = False

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    @property
    def finished(self) -> bool:
        return self._finished

    def cancel(self) -> None:
        self._cancelled = True


class _Runner(QRunnable):
    def __init__(self, fn, args, kwargs, signals: _TaskSignals, handle: TaskHandle):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = dict(kwargs)
        self._signals = signals
        self._handle = handle

    def run(self) -> None:  # pragma: no cover - runs on a worker thread
        try:
            result = self._fn(*self._args, **self._kwargs)
        except Exception as exc:
            log.exception("Task failed: %s", getattr(self._fn, "__name__", self._fn))
            self._signals.error.emit("%s\n\n%s" % (exc, traceback.format_exc(limit=4)))
        else:
            self._signals.done.emit(result)
        finally:
            self._handle._finished = True


class TaskRunner(QObject):
    def __init__(self, parent=None, max_threads: Optional[int] = None):
        super().__init__(parent)
        self._pool = QThreadPool(self)
        if max_threads:
            self._pool.setMaxThreadCount(max_threads)

    @property
    def active_count(self) -> int:
        return self._pool.activeThreadCount()

    def submit(
        self,
        fn: Callable[..., Any],
        *args,
        on_done: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
        on_progress: Optional[Callable] = None,
        on_message: Optional[Callable] = None,
        **kwargs,
    ) -> TaskHandle:
        """Queue a callable. Every callback is delivered on the UI thread."""
        signals = _TaskSignals()
        handle = TaskHandle()

        if on_done:
            signals.done.connect(on_done)
        if on_error:
            signals.error.connect(on_error)
        if on_progress:
            signals.progress.connect(on_progress)
        if on_message:
            signals.message.connect(on_message)

        try:
            params = inspect.signature(fn).parameters
        except (TypeError, ValueError):
            params = {}
        if "progress" in params and "progress" not in kwargs:
            kwargs["progress"] = signals.progress.emit
        if "should_cancel" in params and "should_cancel" not in kwargs:
            kwargs["should_cancel"] = lambda: handle.cancelled
        if "message" in params and "message" not in kwargs:
            kwargs["message"] = signals.message.emit

        runner = _Runner(fn, args, kwargs, signals, handle)
        # Keep the signal object alive for as long as the runner needs it.
        runner._keep_alive = signals
        self._pool.start(runner)
        return handle

    def wait_for_done(self, msec: int = -1) -> bool:
        return self._pool.waitForDone(msec)
