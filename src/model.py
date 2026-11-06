"""The null forecast.

A null model has no trend, seasonality or covariates: it repeats one statistic
of the history window over the whole horizon.  It exists to be the performance
floor on a benchmark and a cheap end-to-end test of the model-runner pipeline.

The interval is the empirical 10th/90th percentile of the same window.  For a
constant window that gives ``q10 == q90 == point``, which is the honest answer
rather than an invented spread.
"""

import numpy as np
import pandas as pd

from series import MIN_CONTEXT, future_values, prepare_target

#: Statistics the model can repeat.
STATISTICS = ("mean", "median", "last")

#: Largest supported horizon; must match ``maxHorizon`` in ``fdo.json``.
MAX_PREDICTION_STEPS = 512

#: Quantile levels of the output interval.
QUANTILE_LEVELS = (0.1, 0.9)


def _point_forecast(values: np.ndarray, statistic: str) -> float:
    """Return the statistic that is repeated over the horizon.

    Args:
        values: Filled history window.
        statistic: One of :data:`STATISTICS`.

    Returns:
        The point forecast.

    Raises:
        ValueError: If the statistic is not supported.
    """
    if statistic == "mean":
        return float(values.mean())
    if statistic == "median":
        return float(np.median(values))
    if statistic == "last":
        return float(values[-1])
    raise ValueError(f"statistic must be one of {', '.join(STATISTICS)}")


def forecast(
    x_series: pd.Series,
    y_series: pd.Series,
    prediction_length: int,
    statistic: str = "mean",
    row_offset: int = 0,
) -> pd.DataFrame:
    """Forecast by repeating one statistic of the history window.

    Args:
        x_series: Time axis of the history window.
        y_series: Target series of the history window.
        prediction_length: Number of steps to forecast.
        statistic: ``mean``, ``median`` or ``last``.
        row_offset: Absolute row index of the first history row in the input
            file.  Used only for a string axis, whose output positions are
            reported relative to the whole input file.

    Returns:
        One row per forecast step: the x column, optionally
        ``x_auto_converted`` for a string axis, the target column and its
        ``_q10``/``_q90`` columns.

    Raises:
        ValueError: If the horizon, statistic, history length or input series
            is invalid.
    """
    if prediction_length <= 0:
        raise ValueError("prediction_length must be > 0")
    if prediction_length > MAX_PREDICTION_STEPS:
        raise ValueError(
            f"prediction_length={prediction_length} exceeds max {MAX_PREDICTION_STEPS} steps"
        )
    if statistic not in STATISTICS:
        raise ValueError(f"statistic must be one of {', '.join(STATISTICS)}")
    if len(x_series) < MIN_CONTEXT:
        raise ValueError(
            f"history must contain at least {MIN_CONTEXT} points (got {len(x_series)}) to forecast"
        )

    values = prepare_target(y_series)
    point = _point_forecast(values, statistic)

    q10, q90 = (float(value) for value in np.quantile(values, QUANTILE_LEVELS))
    # The point must lie inside its own interval: the mean of a very skewed
    # window, or the last value of a window with an older spike, can fall
    # outside the 10th-90th percentile range.
    q10 = min(q10, point)
    q90 = max(q90, point)

    future, positional = future_values(x_series, prediction_length)
    if positional:
        future = [int(value) + row_offset for value in future]

    x_name = x_series.name if x_series.name is not None else "x"
    y_name = y_series.name if y_series.name is not None else "y"

    rows = []
    for index in range(prediction_length):
        row = {x_name: future[index]}
        if positional:
            row["x_auto_converted"] = future[index]
        row[y_name] = point
        row[f"{y_name}_q10"] = q10
        row[f"{y_name}_q90"] = q90
        rows.append(row)

    return pd.DataFrame(rows)
