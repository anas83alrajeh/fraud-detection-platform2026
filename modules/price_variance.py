"""
price_variance.py
------------------------------------------------------------------
Price Variance Analysis — fully local, Pandas-based.

Goal: surface cases where a buyer/employee purchased the SAME material at a
price significantly higher than the peer norm for that material. Such gaps can
signal collusion with a supplier, kickbacks, or inflated invoices.

Method (robust to outliers):
  For each material we compute a robust center (the median unit price) and a
  robust spread (the Median Absolute Deviation, MAD). Each transaction is then
  scored two ways:
     pct_above_median  = (price - median) / median * 100
     robust_z          = 0.6745 * (price - median) / MAD     (modified z-score)
  A transaction is FLAGGED when its price exceeds the median by more than the
  user-defined `threshold_pct`. Severity is graded from how far above it sits.
  We also estimate the monetary overpayment vs. the material median so the
  business impact is quantified, and we roll the flags up by buyer.

The function never mutates the caller's DataFrame and returns ready-to-display
results plus a machine-readable summary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import numpy as np
import pandas as pd


@dataclass
class PriceVarianceResult:
    """Container for the analysis output (display-ready)."""
    flagged: pd.DataFrame              # one row per suspicious transaction
    buyer_summary: pd.DataFrame        # rolled up by buyer
    material_stats: pd.DataFrame       # median/MAD per material (for transparency)
    total_overpaid: float = 0.0        # estimated total excess paid
    flag_count: int = 0
    notes: list[str] = field(default_factory=list)


def _to_numeric(series: pd.Series) -> pd.Series:
    """Coerce a price column to float, tolerating thousands separators / symbols."""
    if pd.api.types.is_numeric_dtype(series):
        return series.astype(float)
    cleaned = (
        series.astype(str)
        .str.replace(r"[^\d,.\-]", "", regex=True)   # drop currency symbols, spaces
        .str.replace(",", "", regex=False)            # remove thousands separators
    )
    return pd.to_numeric(cleaned, errors="coerce")


def _severity(pct_above: float, threshold_pct: float) -> str:
    """Grade severity relative to the chosen threshold."""
    if pct_above >= threshold_pct * 2:
        return "high"
    if pct_above >= threshold_pct * 1.4:
        return "medium"
    return "low"


def analyze_price_variance(
    df: pd.DataFrame,
    item_col: str,
    price_col: str,
    buyer_col: str,
    supplier_col: str | None = None,
    threshold_pct: float = 25.0,
    min_samples: int = 3,
) -> PriceVarianceResult:
    """
    Run the price-variance analysis.

    Parameters
    ----------
    df : pd.DataFrame
        Raw purchase records (one row per purchase line).
    item_col : str
        Column holding the material / item name.
    price_col : str
        Column holding the UNIT price paid.
    buyer_col : str
        Column identifying the buyer / employee who made the purchase.
    supplier_col : str | None
        Optional supplier column (added to output if provided).
    threshold_pct : float
        A transaction is flagged when its price is more than this percentage
        above the material's median price. Default 25%.
    min_samples : int
        Materials with fewer than this many transactions are skipped, because a
        median is meaningless on tiny samples. Default 3.

    Returns
    -------
    PriceVarianceResult
    """
    notes: list[str] = []

    # ---- Validate inputs -------------------------------------------------
    required = [item_col, price_col, buyer_col]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    work = df.copy()
    work[price_col] = _to_numeric(work[price_col])

    before = len(work)
    work = work.dropna(subset=[item_col, price_col, buyer_col])
    work = work[work[price_col] > 0]
    dropped = before - len(work)
    if dropped:
        notes.append(f"Skipped {dropped} rows with missing/invalid price.")

    if work.empty:
        return PriceVarianceResult(
            flagged=pd.DataFrame(), buyer_summary=pd.DataFrame(),
            material_stats=pd.DataFrame(), notes=notes + ["No valid rows to analyze."],
        )

    # ---- Per-material robust statistics ---------------------------------
    grp = work.groupby(item_col)[price_col]
    counts = grp.transform("count")
    median = grp.transform("median")
    # MAD = median(|x - median|); scale-free spread, robust to outliers.
    abs_dev = (work[price_col] - median).abs()
    mad = abs_dev.groupby(work[item_col]).transform("median")

    work = work.assign(
        _count=counts,
        _median=median,
        _mad=mad,
    )

    # Only materials with enough peer transactions are comparable.
    comparable = work[work["_count"] >= min_samples].copy()
    if comparable.empty:
        notes.append(
            f"No material has at least {min_samples} transactions; "
            "lower the minimum to analyze sparse data."
        )
        material_stats = (
            work.groupby(item_col)[price_col]
            .agg(transactions="count", median_price="median",
                 min_price="min", max_price="max")
            .reset_index()
        )
        return PriceVarianceResult(
            flagged=pd.DataFrame(), buyer_summary=pd.DataFrame(),
            material_stats=material_stats, notes=notes,
        )

    # ---- Scoring ---------------------------------------------------------
    comparable["pct_above_median"] = (
        (comparable[price_col] - comparable["_median"]) / comparable["_median"] * 100.0
    )
    # Modified z-score; guard against MAD == 0 (all peers identical).
    safe_mad = comparable["_mad"].replace(0, np.nan)
    comparable["robust_z"] = (
        0.6745 * (comparable[price_col] - comparable["_median"]) / safe_mad
    ).fillna(0.0)
    # Estimated money overpaid vs. the fair (median) price for this material.
    comparable["overpaid_amount"] = (
        comparable[price_col] - comparable["_median"]
    ).clip(lower=0)

    # ---- Flagging --------------------------------------------------------
    flagged = comparable[comparable["pct_above_median"] > threshold_pct].copy()
    flagged["severity"] = flagged["pct_above_median"].apply(
        lambda p: _severity(p, threshold_pct)
    )

    # Build a clean, display-ready table.
    display_cols = {
        item_col: "material",
        buyer_col: "buyer",
        price_col: "price_paid",
    }
    out = flagged.rename(columns=display_cols)
    keep = ["material", "buyer", "price_paid"]
    if supplier_col and supplier_col in flagged.columns:
        out = out.rename(columns={supplier_col: "supplier"})
        keep.append("supplier")

    out["fair_price_median"] = flagged["_median"].round(2)
    out["pct_above_median"] = flagged["pct_above_median"].round(1)
    out["robust_z"] = flagged["robust_z"].round(2)
    out["overpaid_amount"] = flagged["overpaid_amount"].round(2)
    out["severity"] = flagged["severity"]

    keep += ["fair_price_median", "pct_above_median",
             "robust_z", "overpaid_amount", "severity"]
    out = out[keep].sort_values("pct_above_median", ascending=False).reset_index(drop=True)

    # ---- Roll up by buyer -----------------------------------------------
    if not out.empty:
        sev_rank = {"high": 3, "medium": 2, "low": 1}
        buyer_summary = (
            out.assign(_rank=out["severity"].map(sev_rank))
            .groupby("buyer")
            .agg(
                flags=("material", "count"),
                avg_pct_above=("pct_above_median", "mean"),
                total_overpaid=("overpaid_amount", "sum"),
                worst_severity=("_rank", "max"),
            )
            .reset_index()
        )
        rank_sev = {3: "high", 2: "medium", 1: "low"}
        buyer_summary["worst_severity"] = buyer_summary["worst_severity"].map(rank_sev)
        buyer_summary["avg_pct_above"] = buyer_summary["avg_pct_above"].round(1)
        buyer_summary["total_overpaid"] = buyer_summary["total_overpaid"].round(2)
        buyer_summary = buyer_summary.sort_values(
            "total_overpaid", ascending=False
        ).reset_index(drop=True)
    else:
        buyer_summary = pd.DataFrame()

    # ---- Material stats (transparency / audit) --------------------------
    material_stats = (
        comparable.groupby(item_col)
        .agg(
            transactions=(price_col, "count"),
            median_price=(price_col, "median"),
            min_price=(price_col, "min"),
            max_price=(price_col, "max"),
        )
        .round(2)
        .reset_index()
        .rename(columns={item_col: "material"})
    )

    total_overpaid = float(out["overpaid_amount"].sum()) if not out.empty else 0.0
    if out.empty:
        notes.append("No transaction exceeded the threshold.")

    return PriceVarianceResult(
        flagged=out,
        buyer_summary=buyer_summary,
        material_stats=material_stats,
        total_overpaid=round(total_overpaid, 2),
        flag_count=len(out),
        notes=notes,
    )


# ----------------------------------------------------------------------
# Quick self-test when run directly:  python modules/price_variance.py
# ----------------------------------------------------------------------
if __name__ == "__main__":
    demo = pd.DataFrame(
        {
            "material": (["Cement 50kg"] * 6) + (["Steel rebar 12mm"] * 5),
            "unit_price": [22, 23, 22.5, 21.8, 45, 23,         # one buyer pays ~2x
                           310, 305, 308, 600, 312],            # one buyer pays ~2x
            "buyer": ["Ali", "Sara", "Omar", "Lina", "Ali", "Sara",
                      "Ali", "Sara", "Omar", "Khaled", "Lina"],
            "supplier": ["A", "B", "A", "C", "Z", "B",
                         "A", "B", "A", "Z", "C"],
        }
    )
    res = analyze_price_variance(
        demo, "material", "unit_price", "buyer", "supplier",
        threshold_pct=25, min_samples=3,
    )
    print("Flagged transactions:\n", res.flagged, "\n")
    print("By buyer:\n", res.buyer_summary, "\n")
    print("Total overpaid:", res.total_overpaid)
    print("Notes:", res.notes)
