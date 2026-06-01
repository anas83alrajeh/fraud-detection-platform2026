"""
data_loader.py
------------------------------------------------------------------
Safe, local-only ingestion of CSV / Excel files. Nothing leaves the machine.
"""

from __future__ import annotations
import io
import pandas as pd


def load_file(uploaded_file) -> pd.DataFrame:
    """
    Read a Streamlit UploadedFile (CSV or Excel) into a DataFrame.
    Tries common encodings for CSV.
    """
    name = uploaded_file.name.lower()
    raw = uploaded_file.getvalue()

    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(raw))

    # CSV: try utf-8 then fall back to latin-1 / windows-1256 (Arabic).
    for enc in ("utf-8-sig", "utf-8", "windows-1256", "latin-1"):
        try:
            return pd.read_csv(io.BytesIO(raw), encoding=enc)
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue
    # Last resort
    return pd.read_csv(io.BytesIO(raw), encoding="latin-1", engine="python")


def sample_data() -> pd.DataFrame:
    """Built-in demo dataset covering all four detectors."""
    import numpy as np

    rng = np.random.default_rng(7)
    materials = ["Cement 50kg", "Steel rebar 12mm", "Sand m3", "Bricks 1000u", "Paint 20L"]
    base = {"Cement 50kg": 22, "Steel rebar 12mm": 310, "Sand m3": 18,
            "Bricks 1000u": 540, "Paint 20L": 95}
    buyers = ["Ali", "Sara", "Omar", "Lina", "Khaled"]
    suppliers = ["Alpha Co", "Beta Trading", "Gamma Supplies", "NewShell LLC"]

    rows = []
    start = pd.Timestamp("2025-01-01")
    for i in range(400):
        mat = rng.choice(materials)
        buyer = rng.choice(buyers)
        sup = rng.choice(suppliers, p=[0.35, 0.3, 0.3, 0.05])
        price = base[mat] * rng.normal(1.0, 0.04)
        # Inject overpricing for one buyer on cement.
        if buyer == "Khaled" and mat == "Cement 50kg" and rng.random() < 0.6:
            price *= 1.8
        qty = int(rng.integers(5, 50))
        amount = round(price * qty, 2)
        # A few extreme transfer outliers.
        if rng.random() < 0.02:
            amount *= 12
        date = start + pd.Timedelta(days=int(rng.integers(0, 330)))
        # NewShell appears late but big.
        if sup == "NewShell LLC":
            date = start + pd.Timedelta(days=int(rng.integers(300, 330)))
            amount *= 3
        emp_bank = f"EMP-{1000 + buyers.index(buyer)}"
        sup_bank = f"SUP-{2000 + suppliers.index(sup)}"
        # Bank collision: NewShell shares Khaled's account.
        if sup == "NewShell LLC":
            sup_bank = "EMP-1004"
        rows.append({
            "date": date.date(),
            "material": mat,
            "unit_price": round(price, 2),
            "quantity": qty,
            "amount": amount,
            "buyer": buyer,
            "supplier": sup,
            "supplier_bank": sup_bank,
            "employee_bank": emp_bank,
        })
    return pd.DataFrame(rows)
