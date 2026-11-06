"""Time-axis and target-series handling for the null model.

The model needs two things from its input file:

* a numeric target series, with short gaps filled and long gaps rejected, and
* the x values of the forecast horizon, extrapolated from the observed axis.

Both are independent of the forecast statistic, so they live here rather than
in :mod:`model`.
"""

from datetime import date
import warnings

import numpy as np
import pandas as pd

# A forecast of a constant needs at least a few points to be meaningful, and
# the empirical 10th/90th percentiles need a window with some spread.
MIN_CONTEXT = 3

# Missing values are gaps, not zeros.  Interior gaps up to this length are
# interpolated; longer gaps are rejected instead of fabricated.  Gaps at the
# start or end are always filled from the nearest observed value.
MAX_INTERPOLATION_GAP = 8

_DATETIME_TYPES = (date, np.datetime64, pd.Timestamp)


def _require_ordered(x_series: pd.Series, kind: str) -> None:
    """Require x values to be complete, unique and increasing.

    Args:
        x_series: Observed x values.
        kind: Human-readable axis kind for error messages.

    Raises:
        ValueError: If a value is missing, duplicated, or out of order.
    """
    if x_series.isna().any():
        raise ValueError(f"{kind} x values must not contain NaN")
    if not x_series.is_unique:
        raise ValueError(f"{kind} x values must be unique")
    if not x_series.is_monotonic_increasing:
        raise ValueError(f"{kind} x values must be monotonic increasing")


def _require_uniform_step(diffs: pd.Series, kind: str) -> None:
    """Require the differences between x values to be constant.

    Args:
        diffs: Consecutive differences of the x values.
        kind: Human-readable axis kind for error messages.

    Raises:
        ValueError: If the step is not constant.
    """
    first = diffs.iloc[0]
    if pd.api.types.is_timedelta64_dtype(diffs):
        # Compare in nanoseconds with an absolute tolerance: a relative
        # tolerance would silently accept seconds of drift on a daily series.
        values = diffs.map(lambda value: pd.Timedelta(value).value).to_numpy(dtype=np.float64)
        if not np.allclose(values, float(pd.Timedelta(first).value), rtol=0, atol=1):
            raise ValueError(f"{kind} x values must have a uniform step")
        return

    if not np.allclose(diffs.to_numpy(dtype=np.float64), float(first)):
        raise ValueError(f"{kind} x values must have a uniform step")


def coerce_datetime_axis(x_series: pd.Series) -> pd.Series:
    """Convert an axis of dates or date strings to datetimes when possible.

    Object columns that already contain ``date``/``datetime`` objects, and
    string columns whose values all parse as dates, become datetime axes.
    Other string columns (for example ISO weeks such as ``2022-W01``) stay
    unchanged and are treated as ordered labels.

    Args:
        x_series: Observed x values.

    Returns:
        The original series, or a datetime-converted copy.
    """
    if pd.api.types.is_datetime64_any_dtype(x_series):
        return x_series
    if not (pd.api.types.is_object_dtype(x_series) or pd.api.types.is_string_dtype(x_series)):
        return x_series

    values = x_series.dropna()
    if values.empty:
        return x_series
    if values.map(lambda value: isinstance(value, _DATETIME_TYPES)).all():
        return pd.to_datetime(x_series)

    parsed = None
    with warnings.catch_warnings():
        # A failed parse is an expected outcome (string labels such as ISO
        # weeks), so do not surface pandas' per-element parsing warning.
        warnings.simplefilter("ignore")
        parsed = pd.to_datetime(x_series, errors="coerce")
    if parsed.notna().all():
        return parsed
    return x_series


def _datetime_step(x_series: pd.Series):
    """Return the step used to extrapolate a datetime axis.

    A calendar frequency (daily, weekly, monthly, ...) is preferred when
    pandas can infer one, because it survives DST and month lengths.  Otherwise
    the axis must have a uniform timedelta step.

    Args:
        x_series: Validated datetime x values.

    Returns:
        A date offset or a timedelta.

    Raises:
        ValueError: If no frequency is inferable and the step is irregular.
    """
    with warnings.catch_warnings():
        # pandas 3 announces a return-type change for infer_freq; both the old
        # string and the future offset are handled by to_offset below.
        warnings.simplefilter("ignore")
        frequency = pd.infer_freq(pd.DatetimeIndex(x_series))
    if frequency is not None:
        return pd.tseries.frequencies.to_offset(frequency)

    diffs = x_series.diff().dropna()
    _require_uniform_step(diffs, "datetime")
    return diffs.iloc[0]


def future_values(x_series: pd.Series, steps: int) -> tuple[list, bool]:
    """Extrapolate the x values of the forecast horizon.

    Supported axes:

    * datetime-like: calendar frequency or uniform timedelta step;
    * timedelta: uniform step;
    * numeric: uniform, positive step;
    * string: ordered labels, continued as 1-indexed row positions.

    Args:
        x_series: Observed x values of the history window.
        steps: Number of future values to generate.

    Returns:
        ``(values, positional)``.  ``positional`` is true for a string axis;
        the returned values are then row positions rather than labels.

    Raises:
        ValueError: If the axis is unsupported or cannot be extrapolated.
    """
    if len(x_series) < 2:
        raise ValueError("x column must contain at least 2 values to infer the step")

    x_series = coerce_datetime_axis(x_series)

    if pd.api.types.is_datetime64_any_dtype(x_series):
        _require_ordered(x_series, "datetime")
        step = _datetime_step(x_series)
        last = x_series.iloc[-1]
        return [last + step * (index + 1) for index in range(steps)], False

    if pd.api.types.is_timedelta64_dtype(x_series):
        _require_ordered(x_series, "timedelta")
        diffs = x_series.diff().dropna()
        _require_uniform_step(diffs, "timedelta")
        step = diffs.iloc[0]
        last = x_series.iloc[-1]
        return [last + step * (index + 1) for index in range(steps)], False

    if pd.api.types.is_numeric_dtype(x_series):
        _require_ordered(x_series, "numeric")
        diffs = x_series.diff().dropna()
        _require_uniform_step(diffs, "numeric")
        step = float(diffs.iloc[0])
        if step <= 0:
            raise ValueError("numeric x values must have a positive step")
        last = float(x_series.iloc[-1])
        return [last + step * (index + 1) for index in range(steps)], False

    if pd.api.types.is_object_dtype(x_series) or pd.api.types.is_string_dtype(x_series):
        _require_ordered(x_series, "string")
        base = len(x_series)
        return list(range(base + 1, base + 1 + steps)), True

    raise ValueError("x column must be datetime, timedelta, numeric or string")


def _longest_interior_gap(values: np.ndarray) -> int:
    """Return the longest NaN run between the first and last valid value.

    Leading and trailing runs are excluded: they are filled from the nearest
    observed value regardless of their length.

    Args:
        values: Numeric target values.

    Returns:
        Length of the longest interior run of missing values.
    """
    valid = np.flatnonzero(~np.isnan(values))
    if len(valid) < 2:
        return 0

    longest = 0
    current = 0
    for index in range(int(valid[0]) + 1, int(valid[-1])):
        if np.isnan(values[index]):
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def prepare_target(y_series: pd.Series) -> np.ndarray:
    """Validate and fill the target series.

    Args:
        y_series: The series to forecast.

    Returns:
        A float array with no missing values.

    Raises:
        ValueError: If the series is not numeric, is entirely missing, or has
            an interior gap longer than :data:`MAX_INTERPOLATION_GAP`.
    """
    name = y_series.name if y_series.name is not None else "y"
    if not pd.api.types.is_numeric_dtype(y_series):
        raise ValueError(f"target column '{name}' must be numeric")

    values = y_series.astype(np.float64)
    if values.isna().all():
        raise ValueError(f"target column '{name}' must contain at least one non-NaN value")

    gap = _longest_interior_gap(values.to_numpy(dtype=np.float64))
    if gap > MAX_INTERPOLATION_GAP:
        raise ValueError(
            f"target column '{name}' has a NaN gap longer than "
            f"{MAX_INTERPOLATION_GAP} consecutive values ({gap})"
        )

    # Fill only the ends from the nearest observed value (no extrapolation),
    # then interpolate the interior gaps that the check above accepted.
    array = values.to_numpy(dtype=np.float64, copy=True)
    valid = np.flatnonzero(~np.isnan(array))
    first, last = int(valid[0]), int(valid[-1])
    array[:first] = array[first]
    array[last + 1:] = array[last]
    filled = pd.Series(array, index=values.index).interpolate(method="linear", limit=MAX_INTERPOLATION_GAP)
    return filled.to_numpy(dtype=np.float64)
