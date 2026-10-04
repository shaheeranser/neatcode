# Python Adapter

Idiomatic layout, thresholds, and notes for Python projects.

## Typical layouts

**Web / API service** (framework-agnostic, e.g. FastAPI, Flask, Django):

```
app/
├── main.py            # app construction + wiring only
├── <domain>/
│   ├── routes.py      # HTTP layer: parse request, call service, shape response
│   ├── service.py     # business logic; no framework imports
│   ├── repository.py  # persistence; the only place that knows the DB
│   └── models.py      # domain types
└── core/              # config, auth, shared adapters
```

Dependency direction: `routes → service → repository`, and `service` must not import `routes`.
Business logic never imports the web framework.

**Library / package:**

```
src/<pkg>/
├── __init__.py        # minimal; re-export the public API only
├── <module>.py        # one responsibility per module, responsibility docstring at top
└── ...
tests/                 # mirror the package structure
```

**CLI:** keep argument parsing in one `cli.py` that delegates to library functions; do not put
business logic in click/argparse callbacks.

## Thresholds

Defaults from `.neatcode.json`, tuned for Python:

| Metric | Threshold | Notes |
|---|---|---|
| File length (code lines) | 400 | Broken up by responsibility, not by line count alone |
| Function length | 50 | Long functions usually mix phases; split by extracted steps |
| Cyclomatic complexity | 10 | Per function |
| Nesting depth | 4 | Deep nesting → guard clauses / early returns |
| Import cycles | 0 | Use a layered package; break cycles with a shared lower module |

## Python-specific signals

- **`utils.py` / `helpers.py`** that grow past a handful of functions → almost always several real
  modules hiding behind a bucket name. Split by concept.
- **`__init__.py` doing work** (imports with side effects, registration) → move to an explicit
  `setup`/`configure` function. Keep `__init__` to re-exports.
- **A module that imports the app/framework at top level** to run business logic → move the logic
  out and inject the dependency; the framework belongs at the boundary.
- **`if TYPE_CHECKING:` used purely to break a cycle** → usually a sign two modules should share a
  lower module or one should not depend on the other.
- **God class / god module** with many top-level `def`s of unrelated concern → split by
  responsibility.

## Design notes

- **Annotate public functions.** Types are the cheapest documentation and let tooling catch
  boundary mistakes; add `from __future__ import annotations` to avoid runtime import needs.
- **Inject collaborators.** Pass clients, clocks, and file handles in; do not call `datetime.now()`,
  `os.environ`, or open files inside logic that should be testable.
- **Raise with context.** Use `raise ValueError("...") from exc` to preserve the cause; define a
  small exception hierarchy per package rather than raising bare `Exception`.
- **Standard library first.** Reach for `dataclasses`, `pathlib`, `functools`, `itertools` before a
  third-party package; justify anything you add.
- **`__all__` only where it clarifies** the public surface; do not maintain it by hand for large
  modules.

## Refactor notes

- Move one function/class at a time; update imports, then run the project's test command.
- When splitting a module, keep public names re-exported from the old path only during the
  migration, then update call sites and remove the shim — do not leave permanent re-export files.
- Use `pytest`, not ad-hoc asserts, for characterization tests; name them `test_<behavior>`.
- For anything that renders or serializes output, freeze it with a snapshot/golden fixture rather
  than asserting substrings.
