"""
suspicious_transfers.py
------------------------------------------------------------------
Outlier detection on transfer amounts — local ML only.

Two interchangeable methods:
  * Isolation Forest (scikit-learn): unsupervised anomaly detection.
  * Z-Score: classic statistical outlier rule (|z| > threshold).
"""

from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


def _numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def detect_transfers(
    df: pd.DataFrame,
    amount_col: str,
    method: str = "isolation_forest",
    contamination: float = 0.05,
    z_threshold: float = 3.0,
    random_state: int = 42,
) -> pd.DataFrame:
    """
    Return the input rows with two added columns:
      anomaly_score : float (higher = more anomalous)
      is_anomaly    : bool

    method : "isolation_forest" or "zscore".
    """
    if amount_col not in df.columns:
        raise ValueError(f"Column '{amount_col}' not found.")

    work = df.copy()
    work[amount_col] = _numeric(work[amount_col])
    work = work.dropna(subset=[amount_col]).reset_index(drop=True)
    if work.empty:
        return work.assign(anomaly_score=[], is_anomaly=[])

    x = work[[amount_col]].to_numpy()

    if method == "zscore":
        mean, std = work[amount_col].mean(), work[amount_col].std(ddof=0)
        std = std if std and not np.isnan(std) else 1.0
        z = (work[amount_col] - mean) / std
        work["anomaly_score"] = z.abs().round(3)
        work["is_anomaly"] = work["anomaly_score"] > z_threshold
    else:  # isolation_forest
        model = IsolationForest(
            contamination=contamination, random_state=random_state, n_estimators=200
        )
        labels = model.fit_predict(x)                 # -1 = anomaly, 1 = normal
        # Invert decision_function so higher means more anomalous.
        work["anomaly_score"] = (-model.decision_function(x)).round(4)
        work["is_anomaly"] = labels == -1

    return work.sort_values("anomaly_score", ascending=False).reset_index(drop=True)
