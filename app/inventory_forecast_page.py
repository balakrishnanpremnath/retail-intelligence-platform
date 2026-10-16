
"""Streamlit dashboard for forecast-based inventory risk."""

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]

RISK_FILE = ROOT / "models" / "forecast_inventory_risk.csv"
STORES_FILE = ROOT / "data" / "raw" / "stores.csv"

SIGNAL_ORDER = {
    "EXPECTED DEMAND GAP": 0,
    "REORDER LEVEL RISK": 1,
    "ADEQUATE BY POLICY": 2,
}

SIGNAL_COLORS = {
    "EXPECTED DEMAND GAP": "#DC2626",
    "REORDER LEVEL RISK": "#F59E0B",
    "ADEQUATE BY POLICY": "#16A34A",
}


@st.cache_data(ttl=300)
def load_inventory_forecast_risk():
    """Load and validate saved inventory risk snapshots."""

    df = pd.read_csv(
        RISK_FILE,
        parse_dates=["snapshot_date"],
    )

    required = {
        "store_id",
        "product_id",
        "product_name",
        "category",
        "snapshot_date",
        "stock_on_hand",
        "reorder_level",
        "expected_demand",
        "horizon_days",
        "projected_net_stock",
        "expected_coverage_gap_units",
        "stock_signal",
    }

    if df.empty or not required.issubset(df.columns):
        raise ValueError("Inventory risk CSV is empty or incomplete")

    numeric_columns = [
        "stock_on_hand",
        "reorder_level",
        "expected_demand",
        "horizon_days",
        "projected_net_stock",
        "expected_coverage_gap_units",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="raise")

    if not np.isfinite(df[numeric_columns].to_numpy()).all():
        raise ValueError("Inventory risk data contains invalid numbers")

    if (
        df["snapshot_date"].isna().any()
        or df["snapshot_date"].nunique() != 1
    ):
        raise ValueError("Inventory snapshot dates are inconsistent")

    if (
        (df[[
            "stock_on_hand",
            "reorder_level",
            "expected_demand",
            "expected_coverage_gap_units",
        ]] < 0).any().any()
    ):
        raise ValueError("Negative inventory or demand values found")

    if not df["horizon_days"].isin([7, 14]).all():
        raise ValueError("Unexpected forecast horizon")

    if not df["stock_signal"].isin(SIGNAL_ORDER).all():
        raise ValueError("Unexpected inventory risk status")

    if df.duplicated(
        ["store_id", "product_id", "horizon_days"]
    ).any():
        raise ValueError("Duplicate inventory risk records")

    # Ensure both horizons cover the same store-products.
    keys_7 = set(
        zip(
            df.loc[df["horizon_days"] == 7, "store_id"],
            df.loc[df["horizon_days"] == 7, "product_id"],
        )
    )
    keys_14 = set(
        zip(
            df.loc[df["horizon_days"] == 14, "store_id"],
            df.loc[df["horizon_days"] == 14, "product_id"],
        )
    )

    if not keys_7 or keys_7 != keys_14:
        raise ValueError("Forecast horizons have inconsistent coverage")

    # Optional store names from the original synthetic dataset.
    if STORES_FILE.exists():
        stores = pd.read_csv(STORES_FILE)[
            ["store_id", "store_name"]
        ]

        if stores["store_id"].duplicated().any():
            raise ValueError("Duplicate store IDs")

        df = df.merge(
            stores,
            on="store_id",
            how="left",
            validate="many_to_one",
        )
    else:
        df["store_name"] = df["store_id"]

    df["store_name"] = df["store_name"].fillna(df["store_id"])

    return df


def render_inventory_forecast_risk(chart_style):
    """Display projected inventory risks for selected forecast horizon."""

    st.markdown(
        '<div class="section-title">'
        'Forecast-Based Inventory Risk'
        '</div>',
        unsafe_allow_html=True,
    )

    try:
        df = load_inventory_forecast_risk()
    except (OSError, ValueError, KeyError) as exc:
        st.warning("Cannot load forecast inventory risk analysis.")
        st.caption(str(exc))
        return

    snapshot = df["snapshot_date"].iloc[0]

    st.info(
        f"**Inventory snapshot:** {snapshot:%d %B %Y} | "
        "Synthetic dataset | "
        "Projected risks assuming no incoming replenishment."
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        horizon = st.selectbox(
            "Forecast Horizon",
            [7, 14],
            format_func=lambda value: f"{value} days",
            key="inventory_risk_horizon",
        )

    view = df[df["horizon_days"] == horizon].copy()

    store_labels = (
        view[["store_id", "store_name"]]
        .drop_duplicates()
        .sort_values("store_name")
    )

    store_names = dict(zip(
        store_labels["store_id"],
        store_labels["store_name"],
    ))

    with c2:
        store = st.selectbox(
            "Store",
            ["All"] + store_labels["store_id"].tolist(),
            format_func=lambda value: (
                "All Stores"
                if value == "All"
                else store_names[value]
            ),
            key="inventory_risk_store",
        )

    with c3:
        category = st.selectbox(
            "Category",
            ["All"] + sorted(view["category"].unique().tolist()),
            key="inventory_risk_category",
        )

    if store != "All":
        view = view[view["store_id"] == store]

    if category != "All":
        view = view[view["category"] == category]

    if view.empty:
        st.info("No inventory records match your selection.")
        return

    signal_counts = view["stock_signal"].value_counts()

    total_expected = view["expected_demand"].sum()
    total_gap = view["expected_coverage_gap_units"].sum()

    cols = st.columns(4)

    cols[0].metric(
        "Store-Product Records",
        f"{len(view):,}",
    )
    cols[1].metric(
        "Expected Demand",
        f"{total_expected:,.1f} units",
    )
    cols[2].metric(
        "Demand Gap Alerts",
        f"{signal_counts.get('EXPECTED DEMAND GAP', 0):,}",
    )
    cols[3].metric(
        "Potential Gap Units",
        f"{int(total_gap):,}",
    )

    st.markdown("#### Inventory Risk Distribution")

    counts = (
        view["stock_signal"]
        .value_counts()
        .reindex(SIGNAL_ORDER.keys(), fill_value=0)
    )

    fig = go.Figure(go.Bar(
        x=counts.index,
        y=counts.values,
        marker_color=[
            SIGNAL_COLORS[status]
            for status in counts.index
        ],
        text=counts.values,
        textposition="outside",
    ))

    chart_style(fig, f"{horizon}-Day Inventory Risk")
    fig.update_layout(
        height=340,
        xaxis_title=None,
        yaxis_title="Store-product records",
        yaxis=dict(range=[0, max(counts.max() * 1.25, 1)]),
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={"displayModeBar": False},
    )

    st.markdown("#### Priority Inventory Risk Table")

    priority = view.copy()
    priority["priority"] = priority["stock_signal"].map(
        SIGNAL_ORDER
    )

    priority = priority.sort_values(
        ["priority", "expected_coverage_gap_units", "expected_demand"],
        ascending=[True, False, False],
    )

    display_columns = {
        "store_name": "Store",
        "product_name": "Product",
        "stock_on_hand": "Current Stock",
        "expected_demand": "Expected Demand",
        "reorder_level": "Reorder Level",
        "projected_net_stock": "Projected Net Stock",
        "expected_coverage_gap_units": "Gap Units",
        "stock_signal": "Risk Status",
    }

    table = priority[
        list(display_columns)
    ].rename(columns=display_columns)

    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Expected Demand": st.column_config.NumberColumn(
                format="%.2f"
            ),
            "Projected Net Stock": st.column_config.NumberColumn(
                format="%.2f"
            ),
        },
    )

    st.download_button(
        "Download Inventory Risk Report",
        data=table.to_csv(index=False),
        file_name=f"inventory_risk_{horizon}days.csv",
        mime="text/csv",
    )

    st.caption(
        "This is scenario-based decision support, not an "
        "automatic purchase order. Forecast uncertainty, "
        "incoming deliveries and supplier lead times are "
        "not included. A demand gap represents projected "
        "unmet demand under these assumptions."
    )
