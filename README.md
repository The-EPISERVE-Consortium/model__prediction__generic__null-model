# model__prediction__generic__null-model

A deliberately simple forecast model for the EPISERVE platform: it repeats one
statistic of the history window over the forecast horizon. The forecast is
**flat by design** — every step gets the same point and the same interval, and
only the time axis changes. It is the performance floor on a benchmark and a
fast end-to-end check of the model-runner pipeline.

No training, no weights, no network access, no GPU.

**In:** `input.parquet` + `config.json` under `/work/input/`.
**Out:** `predictions.tsv` under `/work/output/`.

## Using this as a template

This repository is also the reference skeleton for a new EPISERVE model: the
container contract, card-driven validation, axis handling, tests, CI and docs are
already wired. To build a model with a real forecasting method, keep the adapter
and replace the core:

| Keep | Replace |
|---|---|
| `run.py`, `config_schema.py`, `series.py` | `src/model.py` — your method |
| `Dockerfile`, CI, contract tests | `fdo.json` — parameters, I/O, resources |
| `documentation/` structure | the pages describing the method |

The core must stay a pure `forecast(x, y, prediction_length, row_offset=0, **params)` that
returns one row per step with a point and q10/q90. Read
[Build Your Own Model](documentation/03-template/build-your-own-model.md) for the
full guide, or [`MODEL_TEMPLATE.md`](MODEL_TEMPLATE.md) for the agent brief.

## Documentation

Rendered documentation site: <https://the-episerve-consortium.github.io/model__prediction__generic__null-model/>

The VitePress sources live in [`documentation/`](documentation/).

The documentation is a committed snapshot, not generated from the code. If you
change something, update `documentation/` in the same pull request. See
[`documentation/_how-to-update.md`](documentation/_how-to-update.md) for the
full regeneration manual, verification steps and troubleshooting.

## Method

1. Take the history window defined by `history_length` and `prediction_offset`.
2. Compute the requested statistic of the target column: `mean`, `median` or
   `last`.
3. Repeat it for every forecast step. This is a **direct multi-step** forecast:
   the statistic is computed once from the observed history, and previous
   forecasts are never fed back into the window. Every output row therefore
   carries the same point and the same q10/q90; only the time axis changes.
4. Use the empirical 10th and 90th percentiles of the same window as the
   interval, clamped so that the point forecast lies inside it. A constant
   window therefore gives `q10 = q90 = point`.

## Input

| Path | Description |
|---|---|
| `/work/input/input.parquet` | At least two columns: the time axis first, the target second. Further columns are ignored. |
| `/work/input/config.json` | Run parameters, see below. |

The time axis may be datetime-like, numeric, timedelta, or an ordered string
column:

- datetime, numeric and timedelta axes must be unique, increasing and evenly
  spaced; the future axis continues that step (calendar frequencies survive
  DST and month lengths),
- a string axis (for example ISO weeks) is continued as 1-indexed row
  positions and the output gains an `x_auto_converted` column.

The target must be numeric. Interior gaps of up to 8 consecutive rows are
interpolated linearly; longer interior gaps are rejected. Gaps at the start or
end are filled from the nearest observed value.

## Output

`/work/output/predictions.tsv`, one row per forecast step (`<y>` is the target
column's name):

| Column | Description |
|---|---|
| `<x>` | Extrapolated x value (row position for a string axis). |
| `x_auto_converted` | 1-indexed absolute row position (string axis only). |
| `<y>` | The repeated statistic. |
| `<y>_q10` / `<y>_q90` | Empirical 10th / 90th percentile of the window. |

## Config

The accepted keys are declared in [`fdo.json`](fdo.json), the model card
(`episerve:parameters`). `src/config_schema.py` loads that declaration and
`src/run.py` checks `config.json` against it at startup with `jsonschema`:
required keys, types, bounds, enum values and no undeclared keys. Optional keys
are filled from their declared default.

| Key | Required | Default | Bounds | Description |
|---|---|---|---|---|
| `history_length` | yes | — | ≥ 3 | Rows in the history window whose statistic is repeated. |
| `prediction_length` | yes | — | 1–512 | Steps to forecast. |
| `prediction_offset` | no | `0` | ≥ 0 | Rows skipped at the end before the history window (back-testing). |
| `statistic` | no | `mean` | `mean`, `median`, `last` | Statistic of the window that is repeated. |

Cross-field rules (for example `history_length + prediction_offset` ≤ input
rows) are listed as `rules` in the card and checked once the data is loaded.

### Check a config without running

```bash
docker run --rm -v $(pwd)/work/input:/work/input <image> --check-config
```

Prints `config.json OK` and exits 0, or `ERROR:` lines and exits 1. It reads
no data and loads no model.

## Model card

[`fdo.json`](fdo.json) follows the EPISERVE
[model-card v1 spec](https://github.com/The-EPISERVE-Consortium/episerve_specs/blob/main/src/episerve_specs/specs/model_card/README.md).
It declares the parameters, the input and output columns, the resources
(`network: false`) and the documentation. CI validates it; locally:

```bash
pip install "git+https://github.com/The-EPISERVE-Consortium/episerve_specs@v0.4.0"
episerve-validate fdo.json
```

The platform reads the card from this repository (the sync flow stores its
sections in the catalog), and the API checks a run's config against
`episerve:parameters` before starting it.

## Develop

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-test.txt
ruff check src tests
mypy src
pytest tests/ -v --cov=src --cov-report=term-missing
```

Run the container contract locally:

```bash
WORK_DIR=./work python src/run.py --check-config
WORK_DIR=./work python src/run.py
docker build -t episerve/generic-null-model:dev .
docker run --rm -v $(pwd)/work/input:/work/input -v $(pwd)/work/output:/work/output \
  episerve/generic-null-model:dev
```

## Release

Images built by CI include the source Git commit SHA in the OCI label
`org.opencontainers.image.revision`.

Push to `main` → CI builds the image, runs lint, type checks and tests inside
it, and pushes `:latest` to GHCR. `git tag v0.1.0 && git push origin v0.1.0`
also publishes the pinned `:v0.1.0` image. `:latest` follows `main` on
non-docs changes; a `vX.Y.Z` tag pins an image for that release. Docs-only
changes do not rebuild the image.

The model is registered in CKAN automatically after its first run through the
model runner; no manual catalog entry is needed.

## Limitations

- The forecast is constant over the horizon: a direct multi-step baseline, not
  a recursive one-step-ahead (sliding-window) forecaster. Feeding each
  prediction back into the window would only damp the last difference and
  converge to a level; it is not implemented.
- No trend, seasonality or covariates, and one series per run.
- The interval describes the spread of the history window, not forecast
  uncertainty.
- A string time axis is continued as row positions, not as new labels.
- Dependencies and the base image are not pinned yet.
