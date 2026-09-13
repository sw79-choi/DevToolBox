# Architecture

## Principles

1. **The core knows nothing about tools.** Dependencies run one way only:
   `tools -> core`. No module under `core/` mentions a specific tool. Delete a
   tool folder and the app still starts.
2. **A tool is one folder.** Adding a feature never means editing an existing
   file. `registry.discover()` scans `devtoolbox/tools/` at startup.
3. **Settings are declared, not drawn.** A tool returns a list of `Field`
   objects; widget creation, defaults, persistence and change notification are
   the core's job.
4. **Logic has no Qt.** Each tool's `logic.py` is pure Python, so it is unit
   testable and reusable from a CLI or a batch script.

## Layers

```
tools/     pdf_merger | json_formatter | hash_tool | base64_tool | + new folder
             ^ (1) scan & register          ^ (2) AppContext injected
core/      ToolRegistry | ConfigManager | TaskRunner | settings builder
           AppContext  <-- the only channel a tool uses to reach the core
             |                                    <-> config.json
             v (3) build tabs, lazily
ui/        MainWindow (category tabs -> tool tabs) | Settings dialog
```

## Tabs

`MainWindow` groups plugins by `ToolMeta.category`, preserving the order the
registry produced (sorted by `ToolMeta.order`), so a category's position is the
lowest `order` among its tools.

* A category with **one** tool shows that tool directly - no inner tab bar.
* A category with **several** tools gets an inner `QTabWidget`.

Tool widgets are built lazily. Each tab holds a `ToolHost`, which constructs the
real widget in its first `showEvent`. That handles both tab levels at once and
keeps startup constant no matter how many tools exist. If construction raises,
the host shows an error page with the traceback instead of taking the app down.

## Boot order

`main.py` does this and nothing else:

1. Prepare paths and logging.
2. Load `config.json`, run migrations if the stored version is older.
3. Discover plugins (`registry.discover()` returns plugins **and** load errors).
4. `config.register_defaults("tools.<id>", plugin.settings_schema())` for each
   plugin. **This must finish before any widget reads a setting.**
5. Build the `QApplication`, apply the theme, create the shared `TaskRunner`.
6. Create `MainWindow` - tabs are placed, widgets are not built yet.
7. Restore window geometry and the last used tab.
8. On close: call `on_close()` on tools that were actually opened, then
   `config.save_now()`.

## The plugin contract

```python
@dataclass(frozen=True)
class ToolMeta:
    id: str                    # settings namespace key; must be unique
    title: str                 # tool tab label
    category: str = "General"  # top-level tab
    order: int = 100           # sort order; also decides category order
    description: str = ""      # tooltip and Settings subtitle
    icon: str | None = None

class ToolPlugin(ABC):
    meta: ToolMeta
    def settings_schema(self) -> list[Field]: return []
    @abstractmethod
    def create_widget(self, ctx: AppContext): ...
    def on_close(self) -> bool: return True      # False vetoes shutdown
```

`AppContext` carries:

| Field | Purpose |
| --- | --- |
| `config` | `ConfigScope` for this tool only - it cannot read or write another tool's keys |
| `app_config` | App-wide scope (`app.*`) |
| `tasks` | Shared `TaskRunner` |
| `log` | Logger named `devtoolbox.tools.<id>` |
| `notify(msg)` | Status bar message |
| `main_window` | Parent window, for dialogs |

## Background work

`TaskRunner` wraps `QThreadPool`. Callbacks are delivered on the UI thread, so
tool code never deals with thread safety.

```python
handle = ctx.tasks.submit(
    merge_pdfs, paths, output, options,   # a plain function from logic.py
    on_progress=self.progress.setValue,
    on_message=ctx.notify,
    on_done=self._on_done,
    on_error=self._on_error,
)
handle.cancel()        # cooperative
```

The runner inspects the worker's signature and injects whichever of
`progress`, `should_cancel` and `message` it declares. That is why `logic.py`
can report progress and honour cancellation without importing Qt.

Cancellation is cooperative: the worker checks `should_cancel()` between units
of work. Threads are never killed.

## Qt binding

`core/qt.py` is the only module that imports PyQt. It exposes `QtWidgets`,
`QtGui`, `Qt`, `Signal`, `exec_()` and normalised enum constants
(`ROLE_USER`, `MB_YES`, `ORIENT_H`, ...). Everything else imports from there, so
switching to PySide6 later is a one-file change.

**Never import PyQt directly outside `core/qt.py`.**

## Error isolation

| Failure | What the user sees |
| --- | --- |
| A tool module raises on import | A `Problems` tab listing the module and its traceback |
| `create_widget()` raises | That tab shows an error page; other tabs work |
| `config.json` is corrupt | Backed up as `config.corrupt.json`; the app starts with defaults |
| A worker raises | `on_error` callback; the app keeps running |
