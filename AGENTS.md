# AGENTS.md

Project context for coding agents working in this repository.

## Using this repository as a template

This repo doubles as the reference skeleton for new EPISERVE models. Keep the
platform adapter (`run.py`, `config_schema.py`, `series.py`, Dockerfile, CI) and
replace `src/model.py` with the new method. Read `MODEL_TEMPLATE.md` before
changing the contract, and `documentation/03-template/build-your-own-model.md`
for the human guide.

## Build & run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-test.txt
WORK_DIR=./work python src/run.py            # needs work/input/{config.json,input.parquet}
WORK_DIR=./work python src/run.py --check-config
docker build -t episerve/generic-null-model:dev .
```

The container contract is `/work/input/config.json` + `/work/input/input.parquet`
→ `/work/output/predictions.tsv`. `WORK_DIR` overrides `/work` for local runs
(`src/run.py:35-44`).

## Testing

```bash
pytest tests/ -v                    # 83 tests
pytest tests/test_model.py -v
pytest tests/test_run.py::test_predictions_are_written_with_the_expected_values -v
```

Tests are the contract. `tests/test_config_schema.py` asserts that `fdo.json`
bounds match the Python constants; update it when you change either side.

## Structure

| Path | Purpose |
|---|---|
| `src/run.py` | entry point, I/O, window selection, exit codes |
| `src/config_schema.py` | loads `episerve:parameters` from `fdo.json`, validates config |
| `src/series.py` | x-axis extrapolation, target gap filling |
| `src/model.py` | point statistic, empirical quantiles, output frame |
| `fdo.json` | model card — the machine-readable contract |
| `tests/` | pytest suite, one file per module plus CLI tests |

## Code style

- Python 3.11, standard library plus pandas/numpy/jsonschema.
- Type hints on public functions; docstrings state args, returns and raises.
- Errors that reach the user go through `_fail` and print `ERROR: <message>` to
  stderr; no tracebacks (`src/run.py:29-32`).
- Keep the forecast pure: no I/O, clock or global state inside `src/model.py`.

## Git workflow

- Branch from `main`; small, focused commits.
- Do not reference AI tools in commit messages and do not add AI attribution
  trailers.
- Push to `main` publishes `:latest`; `git tag vX.Y.Z && git push origin vX.Y.Z`
  publishes a pinned tag (`.github/workflows/publish.yml`).

## Boundaries

- ✅ Always: run `pytest tests/ -v` before committing; keep `fdo.json` and the
  code in sync; cite file:line in docs.
- ⚠️ Ask first: changing the null hypothesis (adding trend/seasonality/covariates),
  renaming parameters, changing the output schema.
- 🚫 Never: commit secrets or credentials; add network calls or model weights;
  overwrite an existing `AGENTS.md`/`CLAUDE.md`; remove the 512-step horizon cap
  without updating the card.

## Documentation

- `README.md` — user-facing usage.
- `documentation/` — generated VitePress wiki (start at `documentation/index.md`).
- `llms.txt` / `documentation/llms-full.txt` — LLM-friendly entry points.
