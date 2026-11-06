"""End-to-end tests of the container entry point."""

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RUN = REPO_ROOT / "src" / "run.py"


def _write_work(tmp_path, config, data=None):
    """Create a temporary ``work/input`` tree.

    Args:
        tmp_path: pytest temporary directory.
        config: Config dictionary (or raw text when a string is passed).
        data: Optional DataFrame written as ``input.parquet``.

    Returns:
        The work directory.
    """
    work = tmp_path / "work"
    input_dir = work / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    (input_dir / "config.json").write_text(config if isinstance(config, str) else json.dumps(config))
    if data is not None:
        data.to_parquet(input_dir / "input.parquet")
    return work


def _run(tmp_path, work, args=()):
    """Run ``src/run.py`` with ``WORK_DIR`` pointing at ``work``."""
    env = os.environ.copy()
    env["WORK_DIR"] = str(work)
    return subprocess.run(
        [sys.executable, str(RUN), *args],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _frame(n=10, target="cases"):
    """Return a simple x/target frame."""
    return pd.DataFrame(
        {
            "date": pd.date_range("2022-01-01", periods=n, freq="D"),
            target: np.arange(1.0, n + 1.0),
        }
    )


# --- config handling ------------------------------------------------------------

def test_check_config_accepts_a_valid_config_without_data(tmp_path):
    work = _write_work(tmp_path, {"history_length": 10, "prediction_length": 5})
    result = _run(tmp_path, work, args=("--check-config",))
    assert result.returncode == 0, result.stderr
    assert "config.json OK" in result.stdout
    assert "input.parquet" not in result.stderr


def test_missing_config_reports_the_resolved_path(tmp_path):
    work = tmp_path / "work"
    (work / "input").mkdir(parents=True)
    result = _run(tmp_path, work)
    assert result.returncode == 1
    assert f"{(work / 'input' / 'config.json').resolve()} not found" in result.stderr


def test_malformed_config_fails_without_a_traceback(tmp_path):
    work = _write_work(tmp_path, "{")
    result = _run(tmp_path, work)
    assert result.returncode == 1
    assert "ERROR: invalid config.json" in result.stderr
    assert "Traceback" not in result.stderr


def test_missing_required_key_fails_before_reading_data(tmp_path):
    work = _write_work(tmp_path, {"prediction_length": 5})
    result = _run(tmp_path, work)
    assert result.returncode == 1
    assert "missing required key: 'history_length'" in result.stderr
    assert "input.parquet not found" not in result.stderr


def test_unknown_key_fails(tmp_path):
    work = _write_work(tmp_path, {"history_length": 10, "prediction_length": 5, "horizon": 2})
    result = _run(tmp_path, work)
    assert result.returncode == 1
    assert "unrecognised key(s): 'horizon'" in result.stderr


def test_unknown_statistic_fails(tmp_path):
    work = _write_work(tmp_path, {"history_length": 10, "prediction_length": 5, "statistic": "max"})
    result = _run(tmp_path, work)
    assert result.returncode == 1
    assert "'statistic' must be one of" in result.stderr


# --- data handling ----------------------------------------------------------------

def test_missing_parquet_reports_the_resolved_path(tmp_path):
    work = _write_work(tmp_path, {"history_length": 3, "prediction_length": 2})
    result = _run(tmp_path, work)
    assert result.returncode == 1
    assert f"{(work / 'input' / 'input.parquet').resolve()} not found" in result.stderr


def test_too_few_columns_is_rejected(tmp_path):
    work = _write_work(
        tmp_path,
        {"history_length": 3, "prediction_length": 2},
        pd.DataFrame({"date": pd.date_range("2022-01-01", periods=5, freq="D")}),
    )
    result = _run(tmp_path, work)
    assert result.returncode == 1
    assert "at least 2 columns" in result.stderr


def test_not_enough_rows_is_rejected(tmp_path):
    work = _write_work(
        tmp_path,
        {"history_length": 10, "prediction_length": 2, "prediction_offset": 1},
        _frame(n=10),
    )
    result = _run(tmp_path, work)
    assert result.returncode == 1
    assert "not enough input data" in result.stderr


def test_prediction_offset_selects_the_window(tmp_path):
    work = _write_work(
        tmp_path,
        {"history_length": 5, "prediction_length": 2, "prediction_offset": 3},
        _frame(n=20),
    )
    result = _run(tmp_path, work)
    assert result.returncode == 0, result.stderr
    assert "Using rows 12-16" in result.stdout


# --- output -------------------------------------------------------------------------

def test_predictions_are_written_with_the_expected_values(tmp_path):
    work = _write_work(
        tmp_path,
        {"history_length": 4, "prediction_length": 2},
        _frame(n=10),
    )
    result = _run(tmp_path, work)
    assert result.returncode == 0, result.stderr

    output = pd.read_csv(work / "output" / "predictions.tsv", sep="\t")
    assert list(output.columns) == ["date", "cases", "cases_q10", "cases_q90"]
    assert len(output) == 2
    # Window is rows 6-9: values 7, 8, 9, 10 -> mean 8.5.
    assert (output["cases"] == 8.5).all()
    assert output["cases_q10"].iloc[0] == pytest.approx(7.3)
    assert output["cases_q90"].iloc[0] == pytest.approx(9.7)


def test_extra_columns_are_ignored(tmp_path):
    data = _frame(n=10)
    data["temperature"] = np.linspace(1.0, 2.0, 10)
    work = _write_work(tmp_path, {"history_length": 4, "prediction_length": 2}, data)
    result = _run(tmp_path, work)
    assert result.returncode == 0, result.stderr

    output = pd.read_csv(work / "output" / "predictions.tsv", sep="\t")
    assert list(output.columns) == ["date", "cases", "cases_q10", "cases_q90"]


def test_median_statistic_is_used(tmp_path):
    data = pd.DataFrame(
        {
            "date": pd.date_range("2022-01-01", periods=5, freq="D"),
            "cases": [1.0, 2.0, 3.0, 4.0, 100.0],
        }
    )
    work = _write_work(
        tmp_path,
        {"history_length": 5, "prediction_length": 2, "statistic": "median"},
        data,
    )
    result = _run(tmp_path, work)
    assert result.returncode == 0, result.stderr
    output = pd.read_csv(work / "output" / "predictions.tsv", sep="\t")
    assert (output["cases"] == 3.0).all()


def test_string_axis_writes_absolute_row_positions(tmp_path):
    data = pd.DataFrame(
        {
            "week": [f"2022-W{index:02d}" for index in range(1, 7)],
            "cases": [10.0, 11.0, 12.0, 13.0, 14.0, 15.0],
        }
    )
    work = _write_work(
        tmp_path,
        {"history_length": 3, "prediction_length": 2, "prediction_offset": 2},
        data,
    )
    result = _run(tmp_path, work)
    assert result.returncode == 0, result.stderr

    output = pd.read_csv(work / "output" / "predictions.tsv", sep="\t")
    assert list(output["week"]) == [5, 6]
    assert list(output["x_auto_converted"]) == [5, 6]


def test_invalid_data_fails_cleanly_without_a_traceback(tmp_path):
    data = _frame(n=20)
    data.loc[5:14, "cases"] = np.nan
    work = _write_work(
        tmp_path,
        {"history_length": 20, "prediction_length": 2},
        data,
    )
    result = _run(tmp_path, work)
    assert result.returncode == 1
    assert "ERROR:" in result.stderr
    assert "NaN gap longer than 8" in result.stderr
    assert "Traceback" not in result.stderr
