"""Premium customer intelligence page for the Retail Intelligence Streamlit app.

Reads synthetic RFM segmentation results from the PostgreSQL analytics view.
Reuses the visual styling helpers defined in app/main.py.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import text

SEGMENT_ORDER = ["High Value", "Loyal", "At Risk"]
SEGMENT_COLORS = {
    "High Value": "#16A34A",
    "Loyal": "#7C3AED",
    "At Risk": "#DC2626",
}


@st.cache_data(ttl=300, show_spinner="Loading customer intelligence...")
def load_customers(_engine):
    """Return one row per customer from the precomputed RFM segmentation view."""
    query = text("""
        SELECT customer_id, customer_name, customer_type, join_date,
               recency, frequency, monetary, segment
        FROM analytics.vw_customer_segments
    """)
    with _engine.connect() as connection:
        return pd.read_sql(query, connection, parse_dates=["join_date"])


def render_customers(get_engine, metric, chart_style):
    """Render filtered customer RFM KPIs, charts and a retention worklist."""
    try:
        customers = load_customers(get_engine())
    except Exception:
        st.error("Customer analytics unavailable. Verify PostgreSQL and the analytics ETL.")
        st.code("docker compose up -d", language="bash")
        st.stop()

    if customers.empty:
        st.warning("The customer segmentation view contains no records.")
        st.stop()

    required = {"customer_id", "customer_name", "customer_type", "recency",
                "frequency", "monetary", "segment"}
    if not required.issubset(customers.columns):
        st.error("Missing customer analytics fields: " + ", ".join(sorted(required - set(customers.columns))))
        st.stop()

    customers = customers.copy()
    for col in ("recency", "frequency", "monetary"):
        customers[col] = pd.to_numeric(customers[col], errors="coerce")
    if customers["customer_id"].isna().any() or customers["customer_id"].duplicated().any():
        st.error("Customer segmentation data has missing or duplicate customer IDs.")
        st.stop()
    if customers[["recency", "frequency", "monetary"]].isna().any().any():
        st.error("The RFM features contain missing or non-numeric values.")
        st.stop()

    st.caption("Synthetic retail customers · Historical RFM reference date: 01 October 2026 · Not a live CRM feed")
    st.markdown('<div class="section-title">Explore customer segments</div>', unsafe_allow_html=True)

    f1, f2 = st.columns(2, gap="large")
    with f1:
        customer_type = st.selectbox(
            "Customer type",
            ["All"] + sorted(customers["customer_type"].dropna().unique().tolist()),
            key="customer_type_filter",
        )
    with f2:
        segment = st.selectbox(
            "RFM segment", ["All"] + SEGMENT_ORDER, key="customer_segment_filter"
        )

    filtered = customers.copy()
    if customer_type != "All":
        filtered = filtered[filtered["customer_type"] == customer_type]
    if segment != "All":
        filtered = filtered[filtered["segment"] == segment]

    if filtered.empty:
        st.info("No customer records match those filters.")
        st.stop()

    counts = filtered["segment"].value_counts()
    total = filtered["customer_id"].nunique()
    average_spend = filtered["monetary"].mean()
    average_recency = filtered["recency"].mean()

    tiles = [
        ("TOTAL CUSTOMERS", f"{total:,}", "#2563EB"),
        ("HIGH VALUE", f"{counts.get('High Value', 0):,}", "#16A34A"),
        ("LOYAL", f"{counts.get('Loyal', 0):,}", "#7C3AED"),
        ("AT RISK", f"{counts.get('At Risk', 0):,}", "#DC2626"),
        ("AVG. CUSTOMER SPEND", f"LKR {average_spend / 1_000:,.2f}K", "#0D9488"),
        ("AVG. RECENCY", f"{average_recency:.1f} days", "#EA580C"),
    ]
    for offset in (0, 3):
        row = st.columns(3, gap="medium")
        for column, (title, value, color) in zip(row, tiles[offset:offset + 3]):
            with column:
                metric(title, value, color)
        st.write("")

    st.markdown('<div class="section-title">Segmentation and spending</div>', unsafe_allow_html=True)
    left, right = st.columns([1, 1.2], gap="large")
    present = [s for s in SEGMENT_ORDER if counts.get(s, 0) > 0]

    with left:
        donut = go.Figure(go.Pie(
            labels=present,
            values=[int(counts[s]) for s in present],
            marker=dict(colors=[SEGMENT_COLORS[s] for s in present]),
            hole=0.64,
            textinfo="percent",
            hovertemplate="%{label}: %{value} customers (%{percent})<extra></extra>",
        ))
        chart_style(donut, "Customer Segment Distribution")
        donut.update_layout(
            showlegend=True,
            legend=dict(orientation="h", x=0, y=-0.1),
            annotations=[dict(x=0.5, y=0.5, text=f"{total:,}", showarrow=False,
                              font=dict(size=25, color="#14213D"))],
        )
        st.plotly_chart(donut, use_container_width=True, config={"displayModeBar": False})

    with right:
        spending = (
            filtered.groupby("segment", as_index=False)["monetary"]
            .mean().sort_values("monetary", ascending=False)
        )
        spend_chart = go.Figure(go.Bar(
            x=spending["segment"],
            y=spending["monetary"],
            marker_color=[SEGMENT_COLORS.get(s, "#2563EB") for s in spending["segment"]],
            text=[f"LKR {x / 1000:,.1f}K" for x in spending["monetary"]],
            textposition="outside",
            hovertemplate="%{x}<br>Average spend: LKR %{y:,.2f}<extra></extra>",
        ))
        chart_style(spend_chart, "Average Historical Spend by Segment")
        spend_chart.update_yaxes(tickprefix="LKR ", tickformat="~s")
        spend_chart.update_layout(margin=dict(l=15, r=15, t=58, b=20))
        st.plotly_chart(spend_chart, use_container_width=True, config={"displayModeBar": False})

    st.markdown('<div class="section-title">Engagement and retention</div>', unsafe_allow_html=True)
    lcol, rcol = st.columns([1.2, 1], gap="large")
    with lcol:
        recency = (filtered.groupby("segment", as_index=False)["recency"]
                   .mean().sort_values("recency", ascending=True))
        recency_chart = go.Figure(go.Bar(
            x=recency["recency"],
            y=recency["segment"],
            orientation="h",
            marker_color=[SEGMENT_COLORS.get(s, "#DC2626") for s in recency["segment"]],
            text=[f"{x:.1f} d" for x in recency["recency"]],
            textposition="outside",
            hovertemplate="%{y}<br>Avg. days since last purchase: %{x:.1f}<extra></extra>",
        ))
        chart_style(recency_chart, "Average Days Since Last Purchase")
        recency_chart.update_layout(xaxis_title="Days", yaxis_title=None)
        st.plotly_chart(recency_chart, use_container_width=True, config={"displayModeBar": False})

    with rcol:
        st.markdown("#### Suggested customer actions")
        st.success("**High Value:** Protect retention with loyalty benefits and personalized service.")
        st.info("**Loyal:** Explore cross-sell recommendations and relevant product bundles.")
        st.warning("**At Risk:** Review historically valuable customers for an opt-in win-back campaign.")
        st.caption("These are illustrative business suggestions, not proven causal effects or real customer outreach instructions.")

    st.markdown('<div class="section-title">At-risk customer retention worklist</div>', unsafe_allow_html=True)
    at_risk = filtered[filtered["segment"] == "At Risk"].copy()
    if at_risk.empty:
        st.info("No At Risk customers match the current filters.")
    else:
        at_risk = at_risk.sort_values(["monetary", "recency"], ascending=[False, False])
        output = at_risk[["customer_id", "customer_name", "customer_type", "recency",
                          "frequency", "monetary"]].rename(columns={
            "customer_id": "Customer ID",
            "customer_name": "Customer Name",
            "customer_type": "Type",
            "recency": "Recency (days)",
            "frequency": "Transactions",
            "monetary": "Lifetime Spend (LKR)",
        })
        st.dataframe(
            output, use_container_width=True, hide_index=True, height=350,
            column_config={
                "Recency (days)": st.column_config.NumberColumn(format="%.0f"),
                "Transactions": st.column_config.NumberColumn(format="%.0f"),
                "Lifetime Spend (LKR)": st.column_config.NumberColumn(format="%.2f"),
            },
        )
        st.download_button(
            "Download filtered At Risk worklist (CSV)",
            data=output.to_csv(index=False).encode("utf-8"),
            file_name="at_risk_customers_synthetic.csv",
            mime="text/csv",
        )
        st.caption(f"{len(output)} synthetic customers, ordered by historical spend. Higher recency = longer inactivity.")

    st.caption("RFM segments were generated with K-Means (3 clusters) from synthetic transaction history. Segment labels are descriptive, not predictions of future customer behavior.")
