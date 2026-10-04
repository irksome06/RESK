"""
Energy Forecasting Candidate Models and Benchmarks.
Includes:
1. Naive Persistence Baseline (Mandatory benchmark: y_hat = lag_1_energy)
2. Moving Average Baseline (y_hat = mean(lags))
3. Ridge Regression
4. Random Forest Regressor
5. Gradient Boosting Regressor
6. XGBoost Regressor
"""

from typing import Dict, Tuple, Any, Optional
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor

try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

XGBOOST_AVAILABLE = HAS_XGBOOST


class NaivePersistenceForecaster(BaseEstimator, RegressorMixin):
    """
    Mandatory Time-Series Benchmark:
    Forecasts next-interval energy using the most recently observed interval energy (lag_1_energy).
    y_hat[t+1] = y[t]
    """

    def __init__(self, lag_column: str = "lag_1_energy"):
        self.lag_column = lag_column

    def fit(self, X, y=None):
        self.n_features_in_ = X.shape[1] if hasattr(X, "shape") else 1
        self.is_fitted_ = True
        return self

    def predict(self, X):
        if isinstance(X, pd.DataFrame):
            if self.lag_column in X.columns:
                return X[self.lag_column].values
            # Fallback to first column
            return X.iloc[:, 0].values
        # Numpy array fallback: assume first feature is lag_1
        X_arr = np.asarray(X)
        return X_arr[:, 0]


class MovingAverageForecaster(BaseEstimator, RegressorMixin):
    """
    Moving-average time-series benchmark:
    Forecasts next-interval energy as the mean of the available historical lags.
    y_hat[t+1] = mean(lag_1, lag_2, lag_3)
    """

    def __init__(self, lag_columns: Optional[list] = None):
        self.lag_columns = lag_columns or ["lag_1_energy", "lag_2_energy", "lag_3_energy"]

    def fit(self, X, y=None):
        self.n_features_in_ = X.shape[1] if hasattr(X, "shape") else 1
        self.is_fitted_ = True
        return self

    def predict(self, X):
        if isinstance(X, pd.DataFrame):
            cols = [c for c in self.lag_columns if c in X.columns]
            if cols:
                return X[cols].mean(axis=1).values
            return X.iloc[:, 0].values
        X_arr = np.asarray(X)
        return np.mean(X_arr[:, : min(3, X_arr.shape[1])], axis=1)


def get_forecast_candidate_models(
    random_state: int = 42,
) -> Dict[str, Tuple[BaseEstimator, Dict[str, Any]]]:
    """
    Returns candidate forecasting estimators with hyperparameter grids.
    Keys are prefixed with 'regressor__' for pipeline compatibility.
    """
    candidates: Dict[str, Tuple[BaseEstimator, Dict[str, Any]]] = {
        "NaivePersistence": (
            NaivePersistenceForecaster(),
            {},
        ),
        "MovingAverage": (
            MovingAverageForecaster(),
            {},
        ),
        "Ridge": (
            Ridge(random_state=random_state),
            {
                "regressor__alpha": [0.1, 1.0, 10.0, 100.0],
            },
        ),
        "RandomForest": (
            RandomForestRegressor(random_state=random_state, n_jobs=-1),
            {
                "regressor__n_estimators": [50, 100],
                "regressor__max_depth": [5, 10],
            },
        ),
        "GradientBoosting": (
            GradientBoostingRegressor(random_state=random_state),
            {
                "regressor__n_estimators": [50, 100],
                "regressor__learning_rate": [0.05, 0.1],
                "regressor__max_depth": [3, 5],
            },
        ),
    }

    if HAS_XGBOOST:
        candidates["XGBoost"] = (
            xgb.XGBRegressor(
                random_state=random_state,
                n_jobs=1,
                objective="reg:squarederror",
                eval_metric="mae",
            ),
            {
                "regressor__n_estimators": [50, 100],
                "regressor__learning_rate": [0.05, 0.1],
                "regressor__max_depth": [3, 5],
            },
        )

    return candidates
