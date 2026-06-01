"""
benford.py
------------------------------------------------------------------
Benford's Law check for invoice amounts (fully local).

Benford's Law states that in many natural numeric datasets, the leading digit d
appears with probability log10(1 + 1/d). Fabricated/altered figures often break
this pattern. We compute the observed leading-digit distribution, compare to the
expected one, and report a chi-square statistic plus a verdict.
"""

from __future__ import annotations
import numpy as np
import pandas as pd

# Expected proportion of each leading digit 1..9 under Benford's Law.
BENFORD_EXPECTED = {d: np.log10(1 + 1 / d) for d in range(1, 10)}

# Chi-square critical value, 8 degrees of freedom, alpha = 0.05.
CHI2_CRIT_8DOF = 15.507


def _leading_digit(values: pd.Series) -> pd.Series:
    s = pd.to_numeric(values, errors="coerce").abs()
    s = s[s > 0]
    # First non-zero digit of the number, scale-independent.
    first = s.apply(lambda x: int(str(x).replace(".", "").lstrip("0")[0]))
    return first


def analyze_benford(df: pd.DataFrame, amount_col: str) -> dict:
    """
    Returns a dict with:
      table         : DataFrame [digit, expected_pct, observed_pct, observed_count]
      chi_square    : float
      suspicious    : bool (True if chi-square exceeds the 0.05 critical value)
      n             : number of valid amounts analyzed
    """
    if amount_col not in df.columns:
        raise ValueError(f"Column '{amount_col}' not found.")

    digits = _leading_digit(df[amount_col])
    n = len(digits)
    if n == 0:
        return {"table": pd.DataFrame(), "chi_square": 0.0,
                "suspicious": False, "n": 0}

    observed_counts = digits.value_counts().reindex(range(1, 10), fill_value=0)
    observed_pct = observed_counts / n

    rows, chi2 = [], 0.0
    for d in range(1, 10):
        exp_p = BENFORD_EXPECTED[d]
        obs_p = float(observed_pct[d])
        exp_count = exp_p * n
        if exp_count > 0:
            chi2 += (observed_counts[d] - exp_count) ** 2 / exp_count
        rows.append({
            "digit": d,
            "expected_pct": round(exp_p * 100, 2),
            "observed_pct": round(obs_p * 100, 2),
            "observed_count": int(observed_counts[d]),
        })

    return {
        "table": pd.DataFrame(rows),
        "chi_square": round(chi2, 2),
        "suspicious": chi2 > CHI2_CRIT_8DOF,
        "n": n,
    }
