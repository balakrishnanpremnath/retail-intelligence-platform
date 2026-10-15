"""Dedicated Sales Analytics page for the Retail Intelligence Streamlit app.

The source is the existing PostgreSQL analytics.vw_sales_detail view.
All figures describe the project's synthetic retail transactions, not live sales.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import text


BLUE = "#2563EB"
GREEN = "#16A34A"
PURPLE = "#7C3AED"
ORANGE = "#F59E0B"
NAVY = "#14213D"


@st.cache_data(ttl=300, show_spinner="Loading sales analytics...")
def load_sales_analytics(_engine):
    """Fetch transactional sales fields from the shared analytics view."""
    sql = text("""
        SELECT full_date, transaction_id, store_name, region,
               product_name, category, quantity, revenue, profit, promotion
        FROM analytics.vw_sales_detail
    """)
    with _engine.connect() as connection:
        sales = pd.read_sql(sql, connection, parse_dates=["full_date"])

    for field in ("quantity", "revenue", "profit"):
        sales[field] = pd.to_numeric(sales[field], errors="raise")
    return sales


def calculate_monthly_growth(sales):
    """Monthly revenue and month-on-month %; no previous period means NA."""
    monthly = (
        sales.set_index("full_date")["revenue"]
        .resample("MS").sum()
        .rename("revenue").reset_index()
        .sort_values("full_date")
    )
    prior = monthly["revenue"].shift(1)
    monthly["growth_pct"] = (
        (monthly["revenue"] - prior)
        .div(prior.where(prior.ne(0)))
        .mul(100)
    )
    return monthly


def calculate_category_margins(sales):
    """Weighted margin = total category profit / total category revenue."""
    groups = sales.groupby("category", as_index=False)[["revenue", "profit"]].sum()
    groups["margin_pct"] = groups["profit"].div(
        groups["revenue"].where(groups["revenue"].ne(0))
    ).mul(100)
    return groups.sort_values("margin_pct", ascending=False)


def calculate_promotion_margins(sales):
    """Compare promotional versus non-promotional transactions."""
    data = sales.copy()
    enabled = (
        data["promotion"].astype("string")
        .str.strip().str.lower().isin(["true", "1", "yes", "t"])
    )
    data["promotion_status"] = enabled.map({True: "Promotion", False: "No Promotion"})
    grouped = data.groupby("promotion_status", as_index=False)[["revenue", "profit"]].sum()
    grouped["margin_pct"] = grouped["profit"].div(
        grouped["revenue"].where(grouped["revenue"].ne(0))
    ).mul(100)
    return grouped


def render_sales(get_engine, metric, chart_style):
    """Render sales deep-dive visuals with filters and verified data."""
    try:
        sales = load_sales_analytics(get_engine())
    except Exception:
        st.error("Cannot load sales analytics from PostgreSQL. Check Docker and the analytics views.")
        st.code("docker compose up -d", language="bash")
        st.stop()

    if sales.empty:
        st.warning("No sales transactions found in the analytics view.")
        st.stop()

    st.caption("Historical transactions · Synthetic retail data · Not a live sales feed")
    st.markdown('<div class="section-title">Explore product & profitability performance</div>',
                unsafe_allow_html=True)

    a, b, c = st.columns(3)
    with a:
        years = ["All"] + [str(value) for value in sorted(sales["full_date"].dt.year.unique())]
        year = st.selectbox("Year", years, key="sales_deep_year")
    with b:
        region = st.selectbox(
            "Region", ["All"] + sorted(sales["region"].dropna().unique().tolist()),
            key="sales_deep_region",
        )
    with c:
        category = st.selectbox(
            "Category", ["All"] + sorted(sales["category"].dropna().unique().tolist()),
            key="sales_deep_category",
        )

    filtered = sales.copy()
    if year != "All":
        filtered = filtered[filtered["full_date"].dt.year == int(year)]
    if region != "All":
        filtered = filtered[filtered["region"] == region]
    if category != "All":
        filtered = filtered[filtered["category"] == category]
    if filtered.empty:
        st.info("No sales match the selected filters.")
        return

    revenue = float(filtered["revenue"].sum())
    profit = float(filtered["profit"].sum())
    margin_pct = 100 * profit / revenue if revenue else 0.0
    product_count = filtered["product_name"].nunique()
    promos = calculate_promotion_margins(filtered)
    promo_revenue = float(promos.loc[promos["promotion_status"] == "Promotion", "revenue"].sum())
    promo_share = 100 * promo_revenue / revenue if revenue else 0.0

    cols = st.columns(4)
    tiles = [
        ("SALES REVENUE", f"LKR {revenue / 1_000_000:,.2f}M", BLUE),
        ("GROSS PROFIT", f"LKR {profit / 1_000_000:,.2f}M", GREEN),
        ("PROFIT MARGIN", f"{margin_pct:.2f}%", PURPLE),
        ("PROMO REVENUE SHARE", f"{promo_share:.1f}%", ORANGE),
    ]
    for column, (label, value, color) in zip(cols, tiles):
        with column:
            metric(label, value, color)
    st.caption(f"{product_count} distinct products · {filtered['transaction_id'].nunique():,} transactions in selection")

    st.markdown('<div class="section-title">Product & category profitability</div>',
                unsafe_allow_html=True)
    top_products = (
        filtered.groupby("product_name", as_index=False)[["revenue", "profit"]].sum()
        .nlargest(10, "profit")
    )
    categories = calculate_category_margins(filtered)
    left, right = st.columns(2, gap="large")
    with left:
        ordered = top_products.sort_values("profit")
        fig = go.Figure(go.Bar(
            x=ordered["profit"], y=ordered["product_name"], orientation="h",
            marker_color=GREEN,
            hovertemplate="%{y}<br>Profit: LKR %{x:,.0f}<extra></extra>",
        ))
        chart_style(fig, "Top 10 Products by Profit")
        fig.update_layout(height=430, margin=dict(l=15, r=32, t=60, b=42))
        fig.update_xaxes(title="Profit (LKR)", tickformat="~s")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with right:
        fig = go.Figure(go.Bar(
            x=categories["category"], y=categories["margin_pct"],
            marker_color=PURPLE,
            text=categories["margin_pct"].map(lambda v: f"{v:.1f}%"),
            textposition="outside",
            hovertemplate="%{x}<br>Margin: %{y:.2f}%<extra></extra>",
        ))
        chart_style(fig, "Profit Margin by Category")
        fig.update_layout(height=430, margin=dict(l=15, r=15, t=60, b=90))
        fig.update_xaxes(tickangle=-35)
        fig.update_yaxes(title="Margin (%)", range=[0, max(10, categories["margin_pct"].max() * 1.25)])
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown('<div class="section-title">Growth & promotion comparison</div>',
                unsafe_allow_html=True)
    monthly = calculate_monthly_growth(filtered)
    left, right = st.columns(2, gap="large")
    with left:
        fig = go.Figure(go.Scatter(
            x=monthly["full_date"], y=monthly["growth_pct"],
            mode="lines+markers", line=dict(color=BLUE, width=3),
            marker=dict(size=6),
            hovertemplate="%{x|%b %Y}<br>MoM Growth: %{y:.2f}%<extra></extra>",
        ))
        chart_style(fig, "Monthly Revenue Growth (MoM %)")
        fig.add_hline(y=0, line=dict(color="#94A3B8", dash="dot"))
        fig.update_layout(height=355)
        fig.update_yaxes(title="Growth (%)", ticksuffix="%")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.caption("The first month in the filtered period has no previous-month comparison.")
    with right:
        promos = promos.set_index("promotion_status").reindex(["No Promotion", "Promotion"]).dropna(subset=["margin_pct"])
        fig = go.Figure(go.Bar(
            x=promos.index, y=promos["margin_pct"],
            marker_color=[BLUE if name == "No Promotion" else ORANGE for name in promos.index],
            text=promos["margin_pct"].map(lambda v: f"{v:.2f}%"),
            textposition="outside",
            hovertemplate="%{x}<br>Profit Margin: %{y:.2f}%<extra></extra>",
        ))
        chart_style(fig, "Promotion vs Non-Promotion Profit Margin")
        fig.update_yaxes(title="Margin (%)", range=[0, max(10, promos["margin_pct"].max() * 1.3)])
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.caption("Observed margin difference; this comparison does not prove a causal impact.")

    st.markdown('<div class="section-title">Store performance & downloadable insights</div>',
                unsafe_allow_html=True)
    stores = filtered.groupby("store_name", as_index=False)[["revenue", "profit"]].sum()
    stores = stores.sort_values("revenue", ascending=False)
    fig = go.Figure()
    for field, label, color in (
        ("revenue", "Revenue", BLUE), ("profit", "Profit", GREEN)
    ):
        fig.add_trace(go.Bar(
            x=stores["store_name"], y=stores[field], name=label,
            marker_color=color,
            hovertemplate="%{x}<br>" + label + ": LKR %{y:,.0f}<extra></extra>",
        ))
    chart_style(fig, "Revenue & Profit by Store")
    fig.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.22),
                      barmode="group", height=350)
    fig.update_yaxes(title="LKR", tickformat="~s")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    insight_table = top_products.sort_values("profit", ascending=False).rename(columns={
        "product_name": "Product", "revenue": "Revenue (LKR)", "profit": "Profit (LKR)"
    })
    st.dataframe(insight_table, use_container_width=True, hide_index=True,
                 column_config={
                     "Revenue (LKR)": st.column_config.NumberColumn(format="%.2f"),
                     "Profit (LKR)": st.column_config.NumberColumn(format="%.2f"),
                 })
    st.download_button(
        "Download Top Products CSV",
        data=insight_table.to_csv(index=False).encode("utf-8"),
        file_name="top_products_by_profit.csv",
        mime="text/csv",
    )
    st.caption("Sales are historical, generated synthetic records. All figures update with the selected filters.")
