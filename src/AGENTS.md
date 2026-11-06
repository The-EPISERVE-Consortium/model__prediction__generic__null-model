# AGENTS.md — src/

Folder-specific context for the model runtime. See the root `AGENTS.md` for
project-wide commands and boundaries.

## Layout

| File | Role |
|---|---|
| `run.py` | CLI entry point; reads `/work`, validates, slices the window, writes TSV |
| `config_schema.py` | Loads `episerve:parameters` from `../fdo.json`, validates with jsonschema |
| `series.py` | Axis extrapolation (`future_values`) and target preparation (`prepare_target`) |
| `model.py` | `forecast()`: point statistic, q10/q90, clamping, output rows |

## Conventions

- Imports are flat (`from series import ...`) because `run.py` inserts `src/`
  into `sys.path` (`run.py:22-26`).
- User-facing failures: `raise ValueError("...")`; `run.py` converts them to
  `ERROR:` lines. Never print tracebacks.
- Keep `model.py` pure: no file I/O, no environment reads, no globals.
- Constants that also appear in the card (`MIN_CONTEXT`, `MAX_PREDICTION_STEPS`)
  must stay in sync with `fdo.json`; `tests/test_config_schema.py` checks this.

## Testing

```bash
pytest tests/test_model.py tests/test_series.py -v
pytest tests/test_config_schema.py -v
```
