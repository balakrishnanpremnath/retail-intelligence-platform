"""Inventory intelligence page for the Retail Intelligence Streamlit app.

Data source: analytics.vw_inventory_intelligence (synthetic snapshot).
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import text

ACTION_COLORS = {
    "URGENT": "#DC2626",
    "REORDER": "#EA580C",
    "REVIEW": "#7C3AED",
    "WATCH": "#F59E0B",
    "OK": "#16A34A",
}

PRIORITY = {"URGENT": 0, "REORDER": 1, "REVIEW": 2, "WATCH": 3, "OK": 4}


@st.cache_data(ttl=300, show_spinner="Loading inventory intelligence...")
def load_inventory(_engine):
    """Load one store-product row per inventory snapshot from PostgreSQL."""
    query = text("""
        SELECT snapshot_date, store_name, region, product_name, category,
               stock_on_hand, reorder_level, estimated_days_cover,
               recommended_reorder_qty, inventory_action, recommendation_reason
        FROM analytics.vw_inventory_intelligence
    """)
    with _engine.connect() as conn:
        return pd.read_sql(query, conn, parse_dates=["snapshot_date"])


def render_inventory(get_engine, metric, chart_style):
    """Render the inventory dashboard using shared Streamlit app styling."""
    try:
        inventory = load_inventory(get_engine())
    except Exception:
        st.error("Unable to load the inventory analytics view. Check PostgreSQL and the analytics ETL.")
        st.code('docker compose up -d', language='bash')
        st.stop()

    if inventory.empty:
        st.warning("No inventory snapshot records are available.")
        st.stop()

    inventory["recommended_reorder_qty"] = pd.to_numeric(
        inventory["recommended_reorder_qty"], errors="coerce"
    ).fillna(0)
    inventory["estimated_days_cover"] = pd.to_numeric(
        inventory["estimated_days_cover"], errors="coerce"
    )

    snapshot = inventory["snapshot_date"].max()
    label = snapshot.strftime("%d %B %Y") if pd.notna(snapshot) else "Unknown date"
    st.caption(f"Inventory snapshot: {label} · Synthetic data · Not a live stock feed")

    st.markdown('<div class="section-title">Explore inventory health</div>', unsafe_allow_html=True)
    col_region, col_category, col_action = st.columns(3)
    with col_region:
        region = st.selectbox(
            "Region", ["All"] + sorted(inventory["region"].dropna().unique().tolist()),
            key="inventory_region",
        )
    with col_category:
        category = st.selectbox(
            "Category", ["All"] + sorted(inventory["category"].dropna().unique().tolist()),
            key="inventory_category",
        )
    with col_action:
        action = st.selectbox(
            "Stock Action", ["All", "URGENT", "REORDER", "REVIEW", "WATCH", "OK"],
            key="inventory_action_filter",
        )

    filtered = inventory.copy()
    if region != "All":
        filtered = filtered[filtered["region"] == region]
    if category != "All":
        filtered = filtered[filtered["category"] == category]
    if action != "All":
        filtered = filtered[filtered["inventory_action"] == action]

    if filtered.empty:
        st.info("No inventory records match the selected filters.")
        st.stop()

    counts = filtered["inventory_action"].value_counts()
    tiles = [
        ("STOCK RECORDS", len(filtered), "#2563EB"),
        ("URGENT ALERTS", int(counts.get("URGENT", 0)), "#DC2626"),
        ("REORDER ALERTS", int(counts.get("REORDER", 0)), "#EA580C"),
        ("REVIEW ITEMS", int(counts.get("REVIEW", 0)), "#7C3AED"),
        ("WATCH ITEMS", int(counts.get("WATCH", 0)), "#F59E0B"),
        ("HEALTHY STOCK", int(counts.get("OK", 0)), "#16A34A"),
    ]
    for start in (0, 3):
        cols = st.columns(3, gap="medium")
        for col, (title, value, color) in zip(cols, tiles[start:start + 3]):
            with col:
                metric(title, f"{value:,}", color)
        st.write("")

    st.markdown('<div class="section-title">Reorder decision intelligence</div>', unsafe_allow_html=True)
    left, right = st.columns([1, 1.2], gap="large")

    with left:
        ordered_actions = [key for key in ACTION_COLORS if counts.get(key, 0)]
        donut = go.Figure(go.Pie(
            labels=ordered_actions,
            values=[int(counts[key]) for key in ordered_actions],
            hole=0.62,
            marker=dict(colors=[ACTION_COLORS[key] for key in ordered_actions]),
            textinfo="percent",
            hovertemplate="%{label}: %{value} records (%{percent})<extra></extra>",
        ))
        chart_style(donut, "Inventory Action Distribution")
        donut.update_layout(
            showlegend=True,
            legend=dict(orientation="h", y=-0.12, x=0),
            annotations=[dict(text=str(len(filtered)), x=0.5, y=0.5,
                              font=dict(size=26, color="#14213D"), showarrow=False)],
        )
        st.plotly_chart(donut, use_container_width=True, config={"displayModeBar": False})

    with right:
        actionable = filtered[filtered["inventory_action"].isin(["URGENT", "REORDER"])]
        by_store = (
            actionable.groupby("store_name", as_index=False)["recommended_reorder_qty"]
            .sum().sort_values("recommended_reorder_qty", ascending=True)
        )
        if by_store.empty:
            st.info("No automatic reorder quantities for these filters.")
        else:
            bars = go.Figure(go.Bar(
                x=by_store["recommended_reorder_qty"],
                y=by_store["store_name"], orientation="h",
                marker_color="#2563EB", text=by_store["recommended_reorder_qty"].astype(int),
                textposition="outside",
                hovertemplate="%{y}<br>%{x:.0f} units<extra></extra>",
            ))
            chart_style(bars, "Recommended Order Units by Store")
            bars.update_layout(xaxis_title="Units", yaxis_title=None)
            st.plotly_chart(bars, use_container_width=True, config={"displayModeBar": False})

    st.markdown('<div class="section-title">Priority reorder recommendations</div>', unsafe_allow_html=True)
    priority_table = filtered[filtered["inventory_action"].isin(["URGENT", "REORDER"])].copy()
    if priority_table.empty:
        st.success("No URGENT or REORDER items match the selected filters.")
    else:
        priority_table["priority"] = priority_table["inventory_action"].map(PRIORITY)
        priority_table = priority_table.sort_values(
            ["priority", "recommended_reorder_qty"], ascending=[True, False]
        )
        priority_table["estimated_days_cover"] = priority_table["estimated_days_cover"].round(1)
        priority_table["recommended_reorder_qty"] = priority_table["recommended_reorder_qty"].astype(int)
        priority_table = priority_table[[
            "store_name", "product_name", "inventory_action", "stock_on_hand",
            "reorder_level", "estimated_days_cover", "recommended_reorder_qty",
            "recommendation_reason",
        ]].rename(columns={
            "store_name": "Store", "product_name": "Product", "inventory_action": "Action",
            "stock_on_hand": "Stock", "reorder_level": "Reorder Level",
            "estimated_days_cover": "Days Cover", "recommended_reorder_qty": "Order Qty",
            "recommendation_reason": "Recommendation Reason",
        })
        st.dataframe(
            priority_table,
            use_container_width=True,
            hide_index=True,
            height=380,
            column_config={
                "Stock": st.column_config.NumberColumn(format="%d"),
                "Reorder Level": st.column_config.NumberColumn(format="%d"),
                "Days Cover": st.column_config.NumberColumn(format="%.1f"),
                "Order Qty": st.column_config.NumberColumn(format="%d"),
            },
        )
        st.caption(f"{len(priority_table)} actionable store-product records, sorted by priority and reorder quantity.")

    st.caption("Reorder quantities are rule-based recommendations using synthetic stock and demand. Confirm supplier lead times before real purchasing.")
