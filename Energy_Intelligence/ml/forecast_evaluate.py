"""
Evaluation Metrics for Energy Forecasting.
Computes:
- MAE: Mean Absolute Error (kWh)
- RMSE: Root Mean Squared Error (kWh)
- R2: Coefficient of Determination
- MASE: Mean Absolute Scaled Error (scaled by in-sample Naive 1-step persistence error)
"""

from typing import Dict, Union, Optional
import numpy as np
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score


def evaluate_forecast(
    y_true: Union[np.ndarray, list],
    y_pred: Union[np.ndarray, list],
    y_train: Optional[Union[np.ndarray, list]] = None,
) -> Dict[str, float]:
    """
    Computes time-series forecast accuracy metrics.

    Args:
        y_true: Ground truth actual energy values on test period
        y_pred: Predicted forecast energy values
        y_train: In-sample training energy values (for MASE scaling denominator)

    Returns:
        Dict with MAE, RMSE, R2, and MASE.
    """
    y_t = np.asarray(y_true, dtype=float)
    y_p = np.asarray(y_pred, dtype=float)

    mae = float(mean_absolute_error(y_t, y_p))
    rmse = float(root_mean_squared_error(y_t, y_p))
    r2 = float(r2_score(y_t, y_p))

    # Compute MASE if y_train is provided
    mase = 1.0
    if y_train is not None and len(y_train) > 1:
        y_tr = np.asarray(y_train, dtype=float)
        # In-sample naive 1-step difference mean: d = mean(|y_t - y_{t-1}|)
        naive_scale = float(np.mean(np.abs(np.diff(y_tr))))
        if naive_scale > 1e-7:
            mase = round(mae / naive_scale, 4)
        else:
            mase = 1.0
    else:
        # Fallback to test naive difference
        test_diff = float(np.mean(np.abs(np.diff(y_t)))) if len(y_t) > 1 else 1.0
        mase = round(mae / test_diff, 4) if test_diff > 1e-7 else 1.0

    return {
        "MAE": round(mae, 6),
        "RMSE": round(rmse, 6),
        "R2": round(r2, 4),
        "MASE": mase,
    }
