# AGENTS.md — tests/

Folder-specific context for the pytest suite. See the root `AGENTS.md`.

## Layout

| File | Covers |
|---|---|
| `test_config_schema.py` | card/model agreement, defaults, error text, card lint |
| `test_model.py` | point statistics, quantiles, clamping, axis output, bounds |
| `test_series.py` | datetime/timedelta/numeric/string axes, DST, gap policy |
| `test_run.py` | CLI end-to-end: config, data errors, TSV contents |

## Conventions

- Plain pytest functions; no classes except where a fixture table is clearer.
- `test_run.py` sets `WORK_DIR` to a `tmp_path` and calls `main()` directly, then
  reads the written TSV. Follow that pattern for new CLI cases.
- Assert on message substrings (`needle`) rather than full strings where the
  wording may evolve.
- Every new parameter or bound needs a test in `test_config_schema.py` that ties
  `fdo.json` to the implementation.

## Commands

```bash
ruff check src tests
mypy src
pytest tests/ -v --cov=src --cov-report=term-missing
pytest tests/test_run.py -k "offset or string" -v
```
