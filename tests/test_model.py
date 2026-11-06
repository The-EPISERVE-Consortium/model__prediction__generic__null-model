"""Tests for the null forecast itself."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from model import MAX_PREDICTION_STEPS, forecast  # noqa: E402


def _series(n=10, name="cases", start="2022-01-01", freq="D"):
    """Return a datetime x series and a simple numeric target."""
    x = pd.Series(pd.date_range(start, periods=n, freq=freq), name="date")
    y = pd.Series(np.arange(1.0, n + 1.0), name=name)
    return x, y


def test_one_row_per_forecast_step():
    x, y = _series()
    assert len(forecast(x, y, prediction_length=7)) == 7


def test_output_columns_and_order():
    x, y = _series(name="value")
    result = forecast(x, y, prediction_length=3)
    assert list(result.columns) == ["date", "value", "value_q10", "value_q90"]


def test_output_columns_default_when_unnamed():
    x = pd.Series(pd.date_range("2022-01-01", periods=5, freq="D"), name=None)
    y = pd.Series(np.arange(1.0, 6.0), name=None)
    result = forecast(x, y, prediction_length=2)
    assert list(result.columns) == ["x", "y", "y_q10", "y_q90"]


def test_mean_statistic():
    x, y = _series(n=10)
    result = forecast(x, y, prediction_length=2, statistic="mean")
    assert (result["cases"] == 5.5).all()


def test_median_statistic():
    x = pd.Series(pd.date_range("2022-01-01", periods=5, freq="D"), name="date")
    y = pd.Series([1.0, 2.0, 3.0, 4.0, 100.0], name="cases")
    result = forecast(x, y, prediction_length=2, statistic="median")
    assert (result["cases"] == 3.0).all()


def test_last_statistic():
    x, y = _series(n=10)
    result = forecast(x, y, prediction_length=2, statistic="last")
    assert (result["cases"] == 10.0).all()


def test_quantiles_are_empirical_quantiles_of_the_window():
    x = pd.Series(pd.date_range("2022-01-01", periods=4, freq="D"), name="date")
    y = pd.Series([1.0, 2.0, 3.0, 4.0], name="cases")
    result = forecast(x, y, prediction_length=2, statistic="mean")
    assert result["cases_q10"].iloc[0] == pytest.approx(1.3)
    assert result["cases_q90"].iloc[0] == pytest.approx(3.7)


def test_constant_window_gives_a_degenerate_interval():
    x = pd.Series(pd.date_range("2022-01-01", periods=5, freq="D"), name="date")
    y = pd.Series([7.0] * 5, name="cases")
    result = forecast(x, y, prediction_length=3)
    assert (result["cases"] == 7.0).all()
    assert (result["cases_q10"] == 7.0).all()
    assert (result["cases_q90"] == 7.0).all()


def test_point_always_lies_inside_the_interval():
    x = pd.Series(pd.date_range("2022-01-01", periods=4, freq="D"), name="date")
    y = pd.Series([1.0, 2.0, 3.0, 100.0], name="cases")
    result = forecast(x, y, prediction_length=2, statistic="last")
    assert (result["cases_q10"] <= result["cases"]).all()
    assert (result["cases"] <= result["cases_q90"]).all()


def test_future_x_is_extrapolated():
    x, y = _series(n=5)
    result = forecast(x, y, prediction_length=3)
    assert list(result["date"]) == list(pd.date_range("2022-01-06", periods=3, freq="D"))


def test_string_axis_uses_absolute_row_positions():
    x = pd.Series(["2022-W01", "2022-W02", "2022-W03"], name="week")
    y = pd.Series([1.0, 2.0, 3.0], name="cases")
    result = forecast(x, y, prediction_length=2, row_offset=10)
    assert list(result["week"]) == [14, 15]
    assert list(result["x_auto_converted"]) == [14, 15]


def test_non_string_axis_has_no_auto_converted_column():
    x, y = _series()
    result = forecast(x, y, prediction_length=2)
    assert "x_auto_converted" not in result.columns


@pytest.mark.parametrize("prediction_length", [0, -1, MAX_PREDICTION_STEPS + 1])
def test_invalid_horizon_is_rejected(prediction_length):
    x, y = _series()
    with pytest.raises(ValueError, match="prediction_length"):
        forecast(x, y, prediction_length=prediction_length)


def test_unknown_statistic_is_rejected():
    x, y = _series()
    with pytest.raises(ValueError, match="statistic must be one of"):
        forecast(x, y, prediction_length=2, statistic="max")


def test_too_short_history_is_rejected():
    x = pd.Series(pd.date_range("2022-01-01", periods=2, freq="D"), name="date")
    y = pd.Series([1.0, 2.0], name="cases")
    with pytest.raises(ValueError, match="at least 3 points"):
        forecast(x, y, prediction_length=2)


def test_non_numeric_target_is_rejected():
    x, _ = _series()
    y = pd.Series(["a"] * 10, name="cases")
    with pytest.raises(ValueError, match="must be numeric"):
        forecast(x, y, prediction_length=2)


def test_long_gap_in_target_is_rejected():
    x, y = _series(n=20)
    y.iloc[5:14] = np.nan
    with pytest.raises(ValueError, match="NaN gap longer than 8"):
        forecast(x, y, prediction_length=2)
