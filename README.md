# 🛡️ Fraud & Anomaly Detection Platform

A **100% offline** platform for detecting fraud and anomalies in invoice and
supplier data. No external / generative-AI APIs are used — only local
statistical analysis and local machine learning (scikit-learn). Your data never
leaves the machine.

Trilingual interface (العربية / English / Deutsch) with automatic
**RTL/LTR** layout switching.

## Features

| Module | Technique |
|---|---|
| **Fake Invoices Detector** | Benford's Law (leading-digit distribution + chi-square) |
| **Price Variance Analysis** | Robust per-material median + MAD; flags buyers overpaying vs. peers |
| **Suspicious Transfers** | Isolation Forest *or* Z-Score outlier detection |
| **Shell Companies Tracker** | New supplier + sudden large dealings; supplier↔employee bank-account collisions |

## Project structure

```
fraud_detection_platform/
├── app.py                      # Streamlit entry point (language switch, routing)
├── requirements.txt
├── README.md
├── .streamlit/
│   └── config.toml             # theme + headless (local) config
├── locales/                    # i18n translation files
│   ├── ar.json
│   ├── en.json
│   └── de.json
├── modules/
│   ├── i18n.py                 # translation loader + t() helper
│   ├── data_loader.py          # safe local CSV/Excel ingestion + sample data
│   ├── price_variance.py       # price-variance detector
│   ├── benford.py              # Benford's Law
│   ├── suspicious_transfers.py # Isolation Forest / Z-Score
│   └── shell_companies.py      # shell-company heuristics
└── components/
    └── styling.py              # RTL/LTR CSS + branded theme
```

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the local URL (default `http://localhost:8501`).

## Usage

1. Pick the interface language from the sidebar dropdown — the whole UI flips
   direction (RTL/LTR) instantly.
2. Upload a CSV/Excel file **or** click *Use sample data* to explore.
3. Open any module, map your columns, tune the thresholds, and run.
4. Export flagged results as CSV.

## Privacy

- No outbound network calls for analysis.
- No generative-AI APIs (OpenAI, OpenRouter, etc.).
- Files are processed in-memory on your machine.
