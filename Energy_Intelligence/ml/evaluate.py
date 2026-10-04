"""
Model Evaluation Metrics for Industrial Energy Baseline.
Reports MAE, RMSE, and R2 with safe zero handling to avoid unstable or infinite MAPE.
"""

from typing import Dict, Union
import numpy as np
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score


def evaluate_predictions(
    y_true: Union[np.ndarray, list],
    y_pred: Union[np.ndarray, list],
) -> Dict[str, float]:
    """
    Computes standard regression evaluation metrics.
    - MAE: Mean Absolute Error (in kWh)
    - RMSE: Root Mean Squared Error (in kWh)
    - R2: Coefficient of Determination (explained variance)
    """
    y_t = np.asarray(y_true, dtype=float)
    y_p = np.asarray(y_pred, dtype=float)

    mae = mean_absolute_error(y_t, y_p)
    rmse = root_mean_squared_error(y_t, y_p)
    r2 = r2_score(y_t, y_p)

    return {
        "MAE": round(float(mae), 6),
        "RMSE": round(float(rmse), 6),
        "R2": round(float(r2), 4),
    }
