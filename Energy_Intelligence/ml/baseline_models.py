"""
Candidate Regression Models and Hyperparameter Search Spaces for Energy Baseline (V2).
Includes:
1. Linear Regression (Baseline reference)
2. Ridge Regression (L2 regularized)
3. Random Forest Regressor (Non-linear ensemble)
4. Gradient Boosting Regressor (Sequential boosting ensemble)
5. XGBoost Regressor (Optimized gradient boosting framework)
"""

from typing import Dict, Tuple, Any
from sklearn.base import BaseEstimator
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor

try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

XGBOOST_AVAILABLE = HAS_XGBOOST


def get_candidate_models(
    random_state: int = 42,
) -> Dict[str, Tuple[BaseEstimator, Dict[str, Any]]]:
    """
    Returns candidate regression estimators paired with bounded hyperparameter search grids.
    Keys are prefixed with 'regressor__' for seamless pipeline integration.
    """
    candidates: Dict[str, Tuple[BaseEstimator, Dict[str, Any]]] = {
        "LinearRegression": (
            LinearRegression(),
            {},
        ),
        "Ridge": (
            Ridge(random_state=random_state),
            {
                "regressor__alpha": [0.01, 0.1, 1.0, 10.0, 100.0],
            },
        ),
        "RandomForest": (
            RandomForestRegressor(random_state=random_state, n_jobs=-1),
            {
                "regressor__n_estimators": [100, 200],
                "regressor__max_depth": [5, 10, 20],
                "regressor__min_samples_split": [2, 5],
            },
        ),
        "GradientBoosting": (
            GradientBoostingRegressor(random_state=random_state),
            {
                "regressor__n_estimators": [100, 200],
                "regressor__learning_rate": [0.03, 0.05, 0.1],
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
                "regressor__n_estimators": [100, 200],
                "regressor__learning_rate": [0.03, 0.05, 0.1],
                "regressor__max_depth": [3, 5],
                "regressor__subsample": [0.8, 1.0],
            },
        )

    return candidates
