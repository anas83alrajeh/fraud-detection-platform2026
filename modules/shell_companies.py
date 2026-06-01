"""
shell_companies.py
------------------------------------------------------------------
Heuristics to surface likely shell/front companies — local only.

Two independent signals:
  1. New suppliers with sudden high volume: suppliers whose first transaction is
     recent yet whose total/largest dealings rank in the top tier.
  2. Bank-account collision: a supplier whose bank account matches an employee's
     bank account (a strong fraud indicator).
"""

from __future__ import annotations
import numpy as np
import pandas as pd


def _norm_account(series: pd.Series) -> pd.Series:
    """Normalize bank account numbers for comparison (strip spaces/dashes)."""
    return (
        series.astype(str)
        .str.replace(r"[\s\-]", "", regex=True)
        .str.upper()
        .replace({"NAN": np.nan, "NONE": np.nan, "": np.nan})
    )


def detect_new_high_volume(
    df: pd.DataFrame,
    supplier_col: str,
    amount_col: str,
    date_col: str,
    recent_quantile: float = 0.75,
    volume_quantile: float = 0.80,
) -> pd.DataFrame:
    """
    Flag suppliers whose first appearance is recent (after the `recent_quantile`
    of all first-transaction dates) AND who show outsized dealings — either a
    high TOTAL volume or a single transaction far above the norm.

    Using max-single-transaction as well as total volume is important: a brand
    new shell company has not had time to accumulate volume, but a sudden very
    large payment is itself a strong red flag.
    """
    for c in (supplier_col, amount_col, date_col):
        if c not in df.columns:
            raise ValueError(f"Column '{c}' not found.")

    work = df.copy()
    work[amount_col] = pd.to_numeric(work[amount_col], errors="coerce")
    work[date_col] = pd.to_datetime(work[date_col], errors="coerce")
    work = work.dropna(subset=[supplier_col, amount_col, date_col])
    if work.empty:
        return pd.DataFrame()

    agg = work.groupby(supplier_col).agg(
        first_seen=(date_col, "min"),
        total_volume=(amount_col, "sum"),
        max_single=(amount_col, "max"),
        transactions=(amount_col, "count"),
    ).reset_index()

    recent_cut = agg["first_seen"].quantile(recent_quantile)
    # Compare the supplier's largest single payment against the population of
    # all individual transactions, not just supplier-level aggregates.
    single_cut = work[amount_col].quantile(volume_quantile)
    volume_cut = agg["total_volume"].quantile(volume_quantile)

    is_recent = agg["first_seen"] >= recent_cut
    is_big = (agg["total_volume"] >= volume_cut) | (agg["max_single"] >= single_cut)

    flagged = agg[is_recent & is_big].copy()
    flagged["total_volume"] = flagged["total_volume"].round(2)
    flagged["max_single"] = flagged["max_single"].round(2)
    return flagged.sort_values("max_single", ascending=False).reset_index(drop=True)


def detect_bank_collisions(
    df: pd.DataFrame,
    supplier_col: str,
    supplier_bank_col: str,
    employee_bank_col: str,
) -> pd.DataFrame:
    """
    Return rows where a supplier's bank account equals an employee's bank account.
    """
    for c in (supplier_col, supplier_bank_col, employee_bank_col):
        if c not in df.columns:
            raise ValueError(f"Column '{c}' not found.")

    work = df.copy()
    work["_sup_acc"] = _norm_account(work[supplier_bank_col])
    work["_emp_acc"] = _norm_account(work[employee_bank_col])

    emp_accounts = set(work["_emp_acc"].dropna())
    matches = work[work["_sup_acc"].isin(emp_accounts) & work["_sup_acc"].notna()].copy()

    if matches.empty:
        return pd.DataFrame()

    cols = [supplier_col, supplier_bank_col, employee_bank_col]
    return matches[cols].drop_duplicates().reset_index(drop=True)
