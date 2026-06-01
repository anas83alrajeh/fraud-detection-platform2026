"""
app.py
==================================================================
Fraud & Anomaly Detection Platform — main Streamlit entry point.

100% local. No external AI / generative APIs. Statistical + local ML only.

Run:   streamlit run app.py
"""

import pandas as pd
import streamlit as st

from modules import i18n
from modules.i18n import t
from modules.data_loader import load_file, sample_data
from modules.price_variance import analyze_price_variance
from modules.benford import analyze_benford
from modules.suspicious_transfers import detect_transfers
from modules.shell_companies import detect_new_high_volume, detect_bank_collisions
from components import styling

# ------------------------------------------------------------------
# Page config + language bootstrap
# ------------------------------------------------------------------
st.set_page_config(page_title="Fraud Detection", page_icon="🛡️", layout="wide")
i18n.init_language()


def column_selector(label: str, df: pd.DataFrame, key: str, default: str | None = None):
    """A dropdown to pick a column, with a neutral placeholder first."""
    options = [t("common.select_column")] + list(df.columns)
    index = 0
    if default and default in df.columns:
        index = options.index(default)
    choice = st.selectbox(label, options, index=index, key=key)
    return None if choice == t("common.select_column") else choice


# ------------------------------------------------------------------
# Sidebar: language switch (drives RTL/LTR), navigation, data source
# ------------------------------------------------------------------
def render_sidebar() -> str:
    with st.sidebar:
        # ---- Language dropdown ----
        opts = i18n.language_options()          # {'ar': 'العربية', ...}
        codes = list(opts.keys())
        current = i18n.get_lang()
        sel = st.selectbox(
            t("sidebar.language"),
            codes,
            index=codes.index(current),
            format_func=lambda c: opts[c],
            key="lang_selector",
        )
        if sel != current:
            i18n.set_lang(sel)
            st.rerun()  # rerun so the whole UI flips direction/font instantly

        st.divider()

        # ---- Navigation ----
        st.subheader(t("sidebar.navigation"))
        pages = {
            "dashboard": t("pages.dashboard"),
            "price_variance": t("pages.price_variance"),
            "benford": t("pages.benford"),
            "transfers": t("pages.transfers"),
            "shell": t("pages.shell"),
        }
        page = st.radio(
            "nav", list(pages.keys()),
            format_func=lambda k: pages[k],
            label_visibility="collapsed",
        )

        st.divider()

        # ---- Data source ----
        st.subheader(t("sidebar.data_section"))
        up = st.file_uploader(
            t("sidebar.upload_label"), type=["csv", "xlsx", "xls"],
            help=t("sidebar.upload_help"),
        )
        if up is not None:
            st.session_state["data"] = load_file(up)
        if st.button(t("sidebar.use_sample")):
            st.session_state["data"] = sample_data()

        df = st.session_state.get("data")
        if df is not None:
            st.success(t("sidebar.loaded_rows", n=len(df)))
        else:
            st.info(t("sidebar.no_data"))

        st.divider()
        st.markdown(
            f'<div style="text-align:center; opacity:.9; font-size:.8rem; '
            f'line-height:1.5;">👨‍💻<br>{t("app.developed_by")}</div>',
            unsafe_allow_html=True,
        )

    return page


# ------------------------------------------------------------------
# Pages
# ------------------------------------------------------------------
def page_dashboard(df):
    st.subheader(t("dashboard.welcome"))
    st.write(t("dashboard.intro"))
    if df is None:
        st.info(t("dashboard.select_module"))
        return

    num_cols = df.select_dtypes("number")
    total_amount = num_cols.sum().max() if not num_cols.empty else 0
    c1, c2, c3, c4 = st.columns(4)
    with c1: styling.kpi(t("dashboard.kpi_total_records"), f"{len(df):,}")
    with c2: styling.kpi(t("dashboard.kpi_total_amount"), f"{total_amount:,.0f}")
    sup = next((c for c in df.columns if "supplier" in c.lower()), None)
    with c3: styling.kpi(t("dashboard.kpi_suppliers"),
                         f"{df[sup].nunique():,}" if sup else "—")
    with c4: styling.kpi(t("dashboard.kpi_flags"), "—")

    st.markdown("### " + t("dashboard.preview"))
    st.dataframe(df.head(50), use_container_width=True)


def page_price_variance(df):
    st.subheader("📈 " + t("price_variance.title"))
    st.caption(t("price_variance.description"))
    if df is None:
        st.warning(t("common.error_no_data")); return

    c1, c2, c3, c4 = st.columns(4)
    with c1: item = column_selector(t("price_variance.col_item"), df, "pv_item", "material")
    with c2: price = column_selector(t("price_variance.col_price"), df, "pv_price", "unit_price")
    with c3: buyer = column_selector(t("price_variance.col_buyer"), df, "pv_buyer", "buyer")
    with c4: supplier = column_selector(t("price_variance.col_supplier"), df, "pv_sup", "supplier")

    c5, c6 = st.columns(2)
    with c5:
        threshold = st.slider(t("price_variance.threshold"), 5, 200, 25, 5)
    with c6:
        min_samples = st.slider(t("price_variance.min_samples"), 2, 20, 3, 1)

    if st.button(t("price_variance.run"), key="run_pv"):
        if not (item and price and buyer):
            st.error(t("common.error_columns")); return
        res = analyze_price_variance(
            df, item, price, buyer, supplier,
            threshold_pct=float(threshold), min_samples=int(min_samples),
        )
        if res.flag_count == 0:
            st.success(t("price_variance.no_flags"))
            return

        m1, m2 = st.columns(2)
        with m1: styling.kpi(t("dashboard.kpi_flags"), f"{res.flag_count}")
        with m2: styling.kpi(t("price_variance.overpaid_total"), f"{res.total_overpaid:,.2f}")

        st.markdown("### " + t("price_variance.results_title"))
        st.dataframe(res.flagged, use_container_width=True)

        st.markdown("### " + t("price_variance.summary_by_buyer"))
        st.dataframe(res.buyer_summary, use_container_width=True)

        st.download_button(
            t("common.download_csv"),
            res.flagged.to_csv(index=False).encode("utf-8-sig"),
            file_name="price_variance_flags.csv", mime="text/csv",
        )


def page_benford(df):
    st.subheader("🔢 " + t("benford.title"))
    st.caption(t("benford.description"))
    if df is None:
        st.warning(t("common.error_no_data")); return

    amount = column_selector(t("benford.col_amount"), df, "bf_amount", "amount")
    if st.button(t("benford.run"), key="run_bf"):
        if not amount:
            st.error(t("common.error_columns")); return
        r = analyze_benford(df, amount)
        if r["n"] == 0:
            st.error(t("common.error_columns")); return

        chart = r["table"].set_index("digit")[["expected_pct", "observed_pct"]]
        chart.columns = [t("benford.expected"), t("benford.observed")]
        st.bar_chart(chart)
        st.metric(t("benford.chi_square"), r["chi_square"])
        if r["suspicious"]:
            st.error("⚠️ " + t("benford.verdict_suspicious"))
        else:
            st.success("✅ " + t("benford.verdict_ok"))


def page_transfers(df):
    st.subheader("💸 " + t("transfers.title"))
    st.caption(t("transfers.description"))
    if df is None:
        st.warning(t("common.error_no_data")); return

    c1, c2 = st.columns(2)
    with c1: amount = column_selector(t("transfers.col_amount"), df, "tr_amount", "amount")
    with c2:
        method_label = st.selectbox(
            t("transfers.method"),
            [t("transfers.method_iso"), t("transfers.method_z")],
        )
    method = "isolation_forest" if method_label == t("transfers.method_iso") else "zscore"

    if method == "isolation_forest":
        contamination = st.slider(t("transfers.contamination"), 0.01, 0.25, 0.05, 0.01)
        z_threshold = 3.0
    else:
        z_threshold = st.slider(t("transfers.z_threshold"), 2.0, 5.0, 3.0, 0.1)
        contamination = 0.05

    if st.button(t("transfers.run"), key="run_tr"):
        if not amount:
            st.error(t("common.error_columns")); return
        out = detect_transfers(df, amount, method, contamination, z_threshold)
        anomalies = out[out["is_anomaly"]]
        if anomalies.empty:
            st.success(t("transfers.no_anomalies"))
        else:
            st.warning(t("transfers.anomalies_found", n=len(anomalies)))
            st.dataframe(anomalies, use_container_width=True)
            st.download_button(
                t("common.download_csv"),
                anomalies.to_csv(index=False).encode("utf-8-sig"),
                file_name="suspicious_transfers.csv", mime="text/csv",
            )


def page_shell(df):
    st.subheader("🏢 " + t("shell.title"))
    st.caption(t("shell.description"))
    if df is None:
        st.warning(t("common.error_no_data")); return

    c1, c2, c3 = st.columns(3)
    with c1: supplier = column_selector(t("shell.col_supplier"), df, "sh_sup", "supplier")
    with c2: amount = column_selector(t("shell.col_amount"), df, "sh_amount", "amount")
    with c3: date = column_selector(t("shell.col_date"), df, "sh_date", "date")
    c4, c5 = st.columns(2)
    with c4: sup_bank = column_selector(t("shell.col_bank"), df, "sh_sbank", "supplier_bank")
    with c5: emp_bank = column_selector(t("shell.col_emp_bank"), df, "sh_ebank", "employee_bank")

    if st.button(t("shell.run"), key="run_sh"):
        found = False
        if supplier and amount and date:
            nhv = detect_new_high_volume(df, supplier, amount, date)
            if not nhv.empty:
                found = True
                st.markdown("### " + t("shell.new_high_volume"))
                st.dataframe(nhv, use_container_width=True)
        if supplier and sup_bank and emp_bank:
            coll = detect_bank_collisions(df, supplier, sup_bank, emp_bank)
            if not coll.empty:
                found = True
                st.markdown("### " + t("shell.bank_match"))
                st.dataframe(coll, use_container_width=True)
        if not found:
            st.success(t("shell.no_findings"))


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def main():
    # Apply direction/font BEFORE drawing widgets so everything flips together.
    styling.inject_theme(i18n.get_direction(), i18n.get_font())

    page = render_sidebar()

    styling.header(t("app.title"), t("app.subtitle"), t("app.offline_badge"))

    df = st.session_state.get("data")
    {
        "dashboard": page_dashboard,
        "price_variance": page_price_variance,
        "benford": page_benford,
        "transfers": page_transfers,
        "shell": page_shell,
    }[page](df)

    st.divider()
    st.caption(t("app.footer"))
    st.markdown(
        f'<div style="text-align:center; margin-top:.4rem;">'
        f'<span style="display:inline-block; background:#0E7C66; color:#fff; '
        f'padding:.3rem .9rem; border-radius:999px; font-size:.82rem; '
        f'font-weight:600;">👨‍💻 {t("app.developed_by")}</span></div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
