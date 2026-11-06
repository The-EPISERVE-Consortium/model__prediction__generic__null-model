"""Entry point of the null model container.

Contract with the model runner:

* read ``/work/input/config.json`` and the first two columns of
  ``/work/input/input.parquet`` (time, target); further columns are ignored,
* write ``/work/output/predictions.tsv``,
* exit 0 on success, non-zero with ``ERROR: <message>`` on stderr otherwise.

``--check-config`` validates the config against the model card and exits
without reading data.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import pandas as pd

# Allow ``python src/run.py`` and imports from the repository root.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config_schema import SchemaError, validate_config
from model import forecast


def _fail(message: str) -> int:
    """Print an ``ERROR:`` line and return the failure exit code."""
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def _work_dir() -> Path:
    """Return the work directory.

    ``WORK_DIR`` wins when set (local runs).  Otherwise use ``./work`` when it
    exists, and fall back to the container's ``/work``.
    """
    if "WORK_DIR" in os.environ:
        return Path(os.environ["WORK_DIR"]).resolve()
    local = Path("./work")
    return local.resolve() if local.exists() else Path("/work")


def main() -> int:
    """Run one forecast.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description="Null forecast model")
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="validate config.json against fdo.json and exit without reading data",
    )
    args = parser.parse_args()

    work = _work_dir()
    input_dir = work / "input"
    output_dir = work / "output"

    config_path = input_dir / "config.json"
    if not config_path.exists():
        return _fail(f"{config_path} not found")

    try:
        config = json.loads(config_path.read_text())
    except json.JSONDecodeError as exc:
        return _fail(f"invalid config.json: {exc}")

    try:
        resolved, config_errors = validate_config(config)
    except SchemaError as exc:
        return _fail(f"model card (fdo.json) parameters are invalid: {exc}")

    if config_errors:
        for error in config_errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    history_length = resolved["history_length"]
    prediction_length = resolved["prediction_length"]
    prediction_offset = resolved["prediction_offset"]
    statistic = resolved["statistic"]
    print(
        "Config: "
        f"history_length={history_length}, "
        f"prediction_length={prediction_length}, "
        f"prediction_offset={prediction_offset}, "
        f"statistic={statistic}"
    )

    if args.check_config:
        print("config.json OK")
        return 0

    data_path = input_dir / "input.parquet"
    if not data_path.exists():
        return _fail(f"{data_path} not found")

    data = pd.read_parquet(data_path)
    print(f"Loaded {len(data)} rows, columns: {list(data.columns)}")

    if len(data.columns) < 2:
        return _fail(
            "input.parquet must have at least 2 columns: the time axis first "
            f"and the target second; got {len(data.columns)}"
        )

    if history_length + prediction_offset > len(data):
        return _fail(
            f"not enough input data: history_length ({history_length}) + "
            f"prediction_offset ({prediction_offset}) = "
            f"{history_length + prediction_offset} rows required, but input.parquet "
            f"has only {len(data)} rows"
        )

    end = len(data) - prediction_offset
    start = end - history_length
    window = data.iloc[start:end]
    x_series = window.iloc[:, 0]
    y_series = window.iloc[:, 1]

    print(f"x column: {x_series.name!r}, target column: {y_series.name!r}")
    print(f"Using rows {start}-{end - 1} ({x_series.iloc[0]} - {x_series.iloc[-1]})")

    try:
        predictions = forecast(
            x_series,
            y_series,
            prediction_length,
            statistic=statistic,
            row_offset=start,
        )
    except ValueError as exc:
        return _fail(str(exc))
    except Exception as exc:  # keep unexpected failures out of the logs as tracebacks
        return _fail(f"model failed: {exc}")

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "predictions.tsv"
    predictions.to_csv(output_path, sep="\t", index=False)
    print(f"Written {len(predictions)} rows to {output_path}")
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
