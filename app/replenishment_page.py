
"""Streamlit view for 14-day replenishment planning scenarios."""

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
PLAN_FILE = ROOT / "models/replenishment_scenarios.csv"
STORES_FILE = ROOT / "data/raw/stores.csv"

ACTIONS = [
    "URGENT REVIEW",
    "MANUAL REVIEW",
    "PLAN REPLENISHMENT",
    "MONITOR",
]

COLORS = {
    "URGENT REVIEW": "#DC2626",
    "MANUAL REVIEW": "#7C3AED",
    "PLAN REPLENISHMENT": "#F59E0B",
    "MONITOR": "#16A34A",
}


@st.cache_data(ttl=300)
def load_replenishment_plan():
    """Read and validate the historical planning scenario."""

    plan = pd.read_csv(
        PLAN_FILE,
        parse_dates=["snapshot_date"],
    )

    required = {
        "store_id",
        "product_id",
        "product_name",
        "snapshot_date",
        "horizon_days",
        "stock_on_hand",
        "reorder_level",
        "expected_demand",
        "planning_target_units",
        "scenario_order_units",
        "forecast_gap_units",
        "planning_action",
        "planning_reason",
    }

    if plan.empty or not required.issubset(plan.columns):
        raise ValueError("Planning scenario CSV is incomplete")

    numeric_columns = [
        "horizon_days",
        "stock_on_hand",
        "reorder_level",
        "expected_demand",
        "planning_target_units",
        "scenario_order_units",
        "forecast_gap_units",
    ]

    for column in numeric_columns:
        plan[column] = pd.to_numeric(
            plan[column],
            errors="raise",
        )

    if (
        not np.isfinite(plan[numeric_columns].to_numpy()).all()
        or (plan[numeric_columns] < 0).any().any()
    ):
        raise ValueError("Invalid planning quantities")

    if not plan["horizon_days"].eq(14).all():
        raise ValueError("Only 14-day scenarios are supported")

    if (
        plan["snapshot_date"].isna().any()
        or plan["snapshot_date"].nunique() != 1
    ):
        raise ValueError("Inconsistent snapshot dates")

    if plan.duplicated(["store_id", "product_id"]).any():
        raise ValueError("Duplicate store-product scenarios")

    if not plan["planning_action"].isin(ACTIONS).all():
        raise ValueError("Unknown planning action")

    if STORES_FILE.exists():
        stores = pd.read_csv(STORES_FILE)[
            ["store_id", "store_name"]
        ]

        if stores["store_id"].duplicated().any():
            raise ValueError("Duplicate store IDs")

        plan = plan.merge(
            stores,
            on="store_id",
            how="left",
            validate="many_to_one",
        )
    else:
        plan["store_name"] = plan["store_id"]

    plan["store_name"] = plan["store_name"].fillna(
        plan["store_id"]
    )

    return plan


def render_replenishment_planning(chart_style):
    """Display explainable forecast-based stock planning."""

    st.markdown(
        '<div class="section-title">'
        'Forecast-Based Replenishment Planning'
        '</div>',
        unsafe_allow_html=True,
    )

    try:
        plan = load_replenishment_plan()
    except (OSError, ValueError, KeyError) as exc:
        st.warning("Replenishment planning data unavailable.")
        st.caption(str(exc))
        return

    snapshot = plan["snapshot_date"].iloc[0]

    st.info(
        f"**Planning snapshot:** {snapshot:%d %B %Y} | "
        "14-day forecast | Synthetic retail dataset | "
        "Scenario-based planning, not actual purchase orders."
    )

    stores = (
        plan[["store_id", "store_name"]]
        .drop_duplicates()
        .sort_values("store_name")
    )

    store_labels = dict(
        zip(stores["store_id"], stores["store_name"])
    )

    left, right = st.columns(2)

    with left:
        store = st.selectbox(
            "Planning Store",
            ["All"] + stores["store_id"].tolist(),
            format_func=lambda value: (
                "All Stores"
                if value == "All"
                else store_labels[value]
            ),
            key="planning_store",
        )

    with right:
        action = st.selectbox(
            "Planning Action",
            ["All"] + ACTIONS,
            key="planning_action_filter",
        )

    filtered = plan.copy()

    if store != "All":
        filtered = filtered[
            filtered["store_id"] == store
        ]

    if action != "All":
        filtered = filtered[
            filtered["planning_action"] == action
        ]

    if filtered.empty:
        st.info("No records match the selected filters.")
        return

    counts = filtered["planning_action"].value_counts()

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Planning Records",
        f"{len(filtered):,}",
    )

    c2.metric(
        "Urgent Reviews",
        f"{counts.get('URGENT REVIEW', 0):,}",
    )

    c3.metric(
        "Plan Replenishment",
        f"{counts.get('PLAN REPLENISHMENT', 0):,}",
    )

    c4.metric(
        "Scenario Order Units",
        f"{int(filtered['scenario_order_units'].sum()):,}",
    )

    st.markdown("#### Planning Action Distribution")

    ordered_counts = counts.reindex(
        ACTIONS,
        fill_value=0,
    )

    fig = go.Figure(go.Bar(
        x=ordered_counts.index,
        y=ordered_counts.values,
        marker_color=[
            COLORS[item] for item in ordered_counts.index
        ],
        text=ordered_counts.values,
        textposition="outside",
    ))

    chart_style(
        fig,
        "14-Day Replenishment Planning Actions",
    )

    fig.update_layout(
        height=340,
        xaxis_title=None,
        yaxis_title="Store-product records",
        yaxis=dict(
            range=[0, max(ordered_counts.max() * 1.25, 1)]
        ),
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={"displayModeBar": False},
    )

    st.markdown("#### Prioritized Planning Scenarios")

    display = filtered.copy()

    priorities = {
        action: index
        for index, action in enumerate(ACTIONS)
    }

    display["priority"] = (
        display["planning_action"].map(priorities)
    )

    display = display.sort_values(
        ["priority", "scenario_order_units"],
        ascending=[True, False],
    )

    columns = {
        "store_name": "Store",
        "product_name": "Product",
        "stock_on_hand": "Current Stock",
        "expected_demand": "14-Day Demand",
        "reorder_level": "Reorder Level",
        "planning_target_units": "Planning Target",
        "scenario_order_units": "Scenario Units",
        "planning_action": "Planning Action",
        "planning_reason": "Reason",
    }

    table = display[
        list(columns)
    ].rename(columns=columns)

    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "14-Day Demand": st.column_config.NumberColumn(
                format="%.2f"
            ),
        },
    )

    st.download_button(
        "Download Replenishment Scenarios",
        data=table.to_csv(index=False),
        file_name="replenishment_planning_14days.csv",
        mime="text/csv",
    )

    st.caption(
        "Scenario units are calculated from forecast demand "
        "plus the existing reorder-level buffer, minus "
        "available stock. They are not confirmed shortages. "
        "Supplier lead times, incoming stock, purchasing "
        "costs and demand uncertainty are not modeled."
    )

