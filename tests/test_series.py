"""Tests for the time-axis and target-series helpers."""

import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from series import MAX_INTERPOLATION_GAP, future_values, prepare_target  # noqa: E402


# --- future_values: datetime axes --------------------------------------------

def test_daily_datetime_axis():
    x = pd.Series(pd.date_range("2022-01-01", periods=5, freq="D"), name="date")
    values, positional = future_values(x, 3)
    assert positional is False
    assert values == list(pd.date_range("2022-01-06", periods=3, freq="D"))


def test_weekly_datetime_axis():
    x = pd.Series(pd.date_range("2022-01-03", periods=5, freq="W"), name="date")
    values, _ = future_values(x, 2)
    assert values == list(pd.date_range("2022-02-13", periods=2, freq="W"))


def test_daily_axis_across_dst():
    x = pd.Series(pd.date_range("2022-03-26", periods=4, freq="D", tz="Europe/Berlin"), name="date")
    values, _ = future_values(x, 2)
    assert values == list(pd.date_range("2022-03-30", periods=2, freq="D", tz="Europe/Berlin"))


def test_object_datetime_axis_is_converted():
    x = pd.Series([datetime(2022, 1, 1), datetime(2022, 1, 2), datetime(2022, 1, 3)], dtype=object, name="date")
    values, positional = future_values(x, 2)
    assert positional is False
    assert values == [pd.Timestamp("2022-01-04"), pd.Timestamp("2022-01-05")]


def test_date_strings_are_parsed_as_datetimes():
    x = pd.Series(["2022-01-01", "2022-01-02", "2022-01-03"], name="date")
    values, positional = future_values(x, 2)
    assert positional is False
    assert values == [pd.Timestamp("2022-01-04"), pd.Timestamp("2022-01-05")]


# --- future_values: other axes ------------------------------------------------

def test_numeric_axis():
    x = pd.Series([0.0, 2.0, 4.0], name="x")
    values, positional = future_values(x, 2)
    assert positional is False
    assert values == [6.0, 8.0]


def test_timedelta_axis():
    x = pd.Series(np.array([0, 1000, 2000], dtype="timedelta64[us]"), name="delta")
    values, _ = future_values(x, 2)
    assert values == [pd.Timedelta(microseconds=3000), pd.Timedelta(microseconds=4000)]


def test_string_axis_continues_as_positions():
    x = pd.Series(["2022-W01", "2022-W02", "2022-W03"], name="week")
    values, positional = future_values(x, 2)
    assert positional is True
    assert values == [4, 5]


# --- future_values: errors ------------------------------------------------------

@pytest.mark.parametrize(
    ("x", "needle"),
    [
        (pd.Series([1.0, 1.0, 2.0], name="x"), "unique"),
        (pd.Series([5.0, 1.0, 2.0], name="x"), "monotonic"),
        (pd.Series([1.0, np.nan, 3.0], name="x"), "NaN"),
        (pd.Series([1.0, 2.0, 4.0], name="x"), "uniform step"),
        (pd.Series(["2022-W01", "2022-W01", "2022-W02"], name="week"), "unique"),
        (pd.Series(["2022-W01", "2022-W03", "2022-W02"], name="week"), "monotonic"),
    ],
)
def test_invalid_axes_are_rejected(x, needle):
    with pytest.raises(ValueError, match=needle):
        future_values(x, 2)


def test_datetime_axis_needs_two_values():
    with pytest.raises(ValueError, match="at least 2"):
        future_values(pd.Series(pd.date_range("2022-01-01", periods=1)), 2)


def test_subsecond_datetime_irregularity_is_rejected():
    x = pd.Series(
        [
            pd.Timestamp("2022-01-01"),
            pd.Timestamp("2022-01-02"),
            pd.Timestamp("2022-01-03 00:00:00.100"),
            pd.Timestamp("2022-01-04"),
        ],
        name="date",
    )
    with pytest.raises(ValueError, match="uniform step"):
        future_values(x, 2)


# --- prepare_target -------------------------------------------------------------

def test_short_interior_gap_is_interpolated():
    y = pd.Series([1.0, np.nan, 3.0, 4.0], name="cases")
    assert list(prepare_target(y)) == [1.0, 2.0, 3.0, 4.0]


def test_long_interior_gap_is_rejected():
    y = pd.Series([1.0] + [np.nan] * (MAX_INTERPOLATION_GAP + 1) + [10.0, 11.0], name="cases")
    with pytest.raises(ValueError, match="NaN gap longer than 8"):
        prepare_target(y)


def test_long_leading_and_trailing_gaps_are_filled():
    leading = pd.Series([np.nan] * 10 + [5.0, 6.0, 7.0], name="cases")
    trailing = pd.Series([5.0, 6.0, 7.0] + [np.nan] * 10, name="cases")
    assert list(prepare_target(leading)) == [5.0] * 10 + [5.0, 6.0, 7.0]
    assert list(prepare_target(trailing)) == [5.0, 6.0, 7.0] + [7.0] * 10


def test_all_missing_target_is_rejected():
    with pytest.raises(ValueError, match="at least one non-NaN"):
        prepare_target(pd.Series([np.nan, np.nan], name="cases"))


def test_non_numeric_target_is_rejected():
    with pytest.raises(ValueError, match="'cases' must be numeric"):
        prepare_target(pd.Series(["low", "high"], name="cases"))


def test_target_keeps_its_name_in_errors():
    with pytest.raises(ValueError, match="'incidence'"):
        prepare_target(pd.Series(["x"], name="incidence"))
