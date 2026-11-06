# Building an EPISERVE model from this repository

This repository is a working, minimal EPISERVE forecast model. It is meant to be
copied: keep the platform plumbing, replace the core method. This file is the
brief for a coding agent doing that work; the human-oriented version is
[`documentation/03-template/build-your-own-model.md`](documentation/03-template/build-your-own-model.md).

## The split you must preserve

```text
platform adapter                         your method
┌─────────────────────────────┐   ┌──────────────────────────┐
│ run.py        I/O, window   │   │ model.py   forecast()    │
│ config_schema card validator│──▶│            point + q10/q90│
│ series.py     axis, gaps    │   └──────────────────────────┘
└─────────────────────────────┘
```

`run.py`, `config_schema.py` and `series.py` know nothing about forecasting.
`model.py` knows nothing about files, the clock, the network or the platform.
Keep that boundary; it is what makes the model testable and portable.

## Invariants (must hold)

- **Container contract:** read `/work/input/config.json` and
  `/work/input/input.parquet`; write `/work/output/predictions.tsv`; exit 0 on
  success, 1 with `ERROR: <message>` on failure.
- **Pure core:** `src/model.py::forecast(...)` performs no file I/O, no network,
  no environment reads and no global mutation.
- **Output schema:** one row per forecast step, the x column, the target point,
  `<target>_q10`, `<target>_q90`; `x_auto_converted` only for a string axis.
- **Card is the contract:** `fdo.json` declares parameters, inputs, outputs,
  resources and documentation; the API server and benchmark workflow read it.
- **Card/code agreement:** `tests/test_config_schema.py` ties bounds and
  constants to the card; keep it green.
- **Determinism:** the same input and config produce the same output. Seed any
  stochastic method and record the seed as a parameter.
- **Horizon cap:** `episerve:task.maxHorizon` equals `MAX_PREDICTION_STEPS`.
- **Declared resources only:** no network unless `network: true`; declare CPU,
  memory and GPU honestly.
- **No future leakage:** never use rows after the history window, and never read
  the reference/truth file.

## What to keep and what to replace

| Path | Action | Why |
|---|---|---|
| `src/run.py` | **Keep** | Container contract, window slice, exit codes |
| `src/config_schema.py` | **Keep** | Card-driven validation and defaults |
| `src/series.py` | **Keep** | Axis extrapolation and gap policy |
| `src/model.py` | **Replace** | Your forecasting method |
| `tests/test_run.py`, `test_series.py`, `test_config_schema.py` | **Keep, extend** | Contract tests |
| `tests/test_model.py` | **Replace/extend** | Tests for your method |
| `fdo.json` | **Edit** | Name, parameters, I/O, resources, docs |
| `Dockerfile`, `requirements*.txt` | **Edit** | Your dependencies |
| `.github/workflows/publish.yml` | **Keep** | Card check, in-image tests, GHCR |
| `documentation/` | **Edit** | Keep the docs truthful |
| `README.md` | **Edit** | Name, method, usage |

## Agent workflow

1. **Read first:** `fdo.json`, `src/model.py`, `src/series.py`,
   `tests/test_model.py`, `README.md`. Do not infer the contract from filenames.
2. **Resolve the task before coding.** Ask the user, or read the benchmark:
   - forecast / nowcast / classification?
   - point only, or quantiles? which levels?
   - horizon and history bounds?
   - covariates allowed? which columns?
   - one series per run or panel?
   - CPU/memory/GPU/network budget and typical runtime?
3. **Update the card first.** Add parameters with type, bounds, default and
   `parameterRoles` (`horizon`, `history`, `offset`). Add or change
   `episerve:inputs`/`outputs` only if the contract really changes.
4. **Implement the core.** Keep the signature and output shape; delegate axis
   and gap handling to `series.py`; return point + quantiles.
5. **Test the core.** Assert shape, columns, values on a hand-computed series,
   quantile ordering (`q10 <= point <= q90`), determinism, and edge cases
   (constant series, short window, NaN handling, max horizon).
6. **Update the docs** under `documentation/` in the same change.
7. **Verify locally:** `pytest tests/ -v`, `docker build`, `--check-config`.
8. **Publish:** push `main` for `:latest`, tag `vX.Y.Z` for a pinned image.
9. **Register:** the first successful run through the model runner creates the
   CKAN entry; then add a qualifying run to a benchmark.
10. **Report** the image tag, the run QID, the benchmark entry and the metrics.

## Core method guidance

- **Inputs:** you receive the history window as two `pandas.Series` (x and y)
  already sliced and gap-filled. Do not re-read the parquet file.
- **Output:** build a `DataFrame` with the same column names as the input target.
- **Quantiles:** emit real predictive quantiles if the method supports them; if
  not, derive them from a residual/backtest distribution, not from an arbitrary
  constant width.
- **Runtime:** the platform expects seconds, not minutes, unless the card says
  otherwise. Cache weights in the image, not at run time.
- **Dependencies:** pin them for reproducibility; keep the image small.
- **Failure:** raise `ValueError` with a user-facing message for bad input; let
  `run.py` format it as `ERROR:`.

## Anti-patterns

| Don't | Why |
|---|---|
| Read `/work/input/input.parquet` inside `model.py` | Breaks purity and tests |
| Hardcode column names | The model must be dataset-agnostic |
| Add parameters only in Python | The card is the contract; the API rejects undeclared keys |
| Use rows after the history window | Leaks the future and invalidates the benchmark |
| Download weights at run time | `network: false` is the default; runs must be reproducible |
| Return a different column layout | Scoring and the runner expect the declared schema |
| Ignore `maxHorizon` | Unbounded horizons blow up memory and runtime |
| Train during inference | The benchmark measures forecasting, not fitting |

## Definition of done

- [ ] `pytest tests/ -v` passes.
- [ ] `fdo.json` validates against the model-card spec.
- [ ] `--check-config` accepts the example config and rejects unknown keys.
- [ ] The image builds and runs the container contract end to end.
- [ ] The card and the code agree on bounds and constants.
- [ ] The docs describe the new method, parameters and limitations.
- [ ] The first run is registered and, if applicable, added to a benchmark.
