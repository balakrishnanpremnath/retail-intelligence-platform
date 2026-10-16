import os
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')

st.set_page_config(page_title='Retail Intelligence | Analytics', page_icon='📊', layout='wide', initial_sidebar_state='expanded')

st.markdown('''
<style>
.stApp {background: #F4F7FB; color: #14213D;}
[data-testid="stSidebar"] {background: #FFFFFF; border-right: 1px solid #E2E8F0;}
.block-container {padding-top: 1.6rem; max-width: 1500px;}
.hero {background: linear-gradient(115deg, #14213D, #1E40AF); padding: 30px 34px; border-radius: 18px; color: #FFFFFF; margin-bottom: 18px; box-shadow: 0 12px 25px rgba(20,33,61,.12);}
.hero h1 {color: #FFFFFF; margin: 0 0 6px; font-size: 2rem; font-weight: 750;}
.hero p {color: #CBD5E1; font-size: 0.95rem; margin: 0;}
.metric-card {background: #FFFFFF; border: 1px solid #E2E8F0; border-top: 4px solid var(--accent); border-radius: 14px; padding: 18px; min-height: 108px; box-shadow: 0 4px 14px rgba(15,23,42,.035);}
.metric-title {color: #64748B; font-size: .82rem; font-weight: 600; margin-bottom: 10px;}
.metric-value {color: #0F172A; font-size: 1.6rem; font-weight: 800; letter-spacing: -0.03em; white-space: nowrap;}
.section-title {font-size: 1.05rem; color: #14213D; font-weight: 750; margin: 16px 0 8px;}
.small-note {font-size: .8rem; color: #64748B;}
[data-testid="stPlotlyChart"] {border: 1px solid #E2E8F0; background: #FFFFFF; border-radius: 14px; padding: 10px;}
</style>
''', unsafe_allow_html=True)

@st.cache_resource
def get_engine():
    required = ['POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD']
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise ValueError('Missing .env settings: ' + ', '.join(missing))
    url = URL.create(
        'postgresql+psycopg2',
        username=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD'),
        host=os.getenv('POSTGRES_HOST'),
        port=int(os.getenv('POSTGRES_PORT')),
        database=os.getenv('POSTGRES_DB'),
    )
    return create_engine(url, pool_pre_ping=True)

@st.cache_data(ttl=300)
def load_sales():
    sql = text('''
        SELECT full_date, transaction_id, store_name, region,
               product_name, category, quantity, revenue, profit
        FROM analytics.vw_sales_detail
    ''')
    with get_engine().connect() as conn:
        return pd.read_sql(sql, conn, parse_dates=['full_date'])

def compact(amount, currency=False):
    value = float(amount)
    if abs(value) >= 1_000_000:
        result = f'{value / 1_000_000:,.2f}M'
    elif abs(value) >= 1_000:
        result = f'{value / 1_000:,.2f}K'
    else:
        result = f'{value:,.0f}'
    return f'LKR {result}' if currency else result

def metric(label, value, color):
    st.markdown(
        f'<div class="metric-card" style="--accent:{color}">'
        f'<div class="metric-title">{label}</div>'
        f'<div class="metric-value">{value}</div></div>',
        unsafe_allow_html=True,
    )

def chart_style(fig, title):
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color='#14213D')),
        paper_bgcolor='#FFFFFF', plot_bgcolor='#FFFFFF',
        margin=dict(l=15, r=15, t=58, b=20), height=350,
        font=dict(color='#475569'), showlegend=False,
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor='#E9EEF5', zeroline=False),
    )
    return fig

with st.sidebar:
    st.markdown('## 📊 Retail Intelligence')
    st.caption('BUSINESS ANALYTICS PLATFORM')
    st.divider()
    page = st.radio('Workspace', ['Executive Overview', 'Sales Analytics', 'Inventory Intelligence', 'Customer Intelligence', 'Demand Forecasting'])
    st.divider()
    st.caption('Synthetic retail data · Portfolio demonstration')

st.markdown(f'<div class="hero"><h1>{page}</h1><p>Real business insights powered by Python and PostgreSQL</p></div>', unsafe_allow_html=True)

if page == 'Executive Overview':
    try:
        sales = load_sales()
    except Exception:
        st.error('Cannot read PostgreSQL. Check Docker and the local .env configuration.')
        st.code('docker compose up -d', language='bat')
        st.stop()

    if sales.empty:
        st.warning('No sales records are available in the analytics view.')
        st.stop()

    st.markdown('<div class="section-title">Explore your performance</div>', unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)
    with f1:
        years = ['All'] + [str(y) for y in sorted(sales['full_date'].dt.year.unique())]
        year = st.selectbox('Year', years)
    with f2:
        region = st.selectbox('Region', ['All'] + sorted(sales['region'].dropna().unique().tolist()))
    with f3:
        category = st.selectbox('Category', ['All'] + sorted(sales['category'].dropna().unique().tolist()))

    filtered = sales.copy()
    if year != 'All':
        filtered = filtered[filtered['full_date'].dt.year == int(year)]
    if region != 'All':
        filtered = filtered[filtered['region'] == region]
    if category != 'All':
        filtered = filtered[filtered['category'] == category]
    if filtered.empty:
        st.info('No data matches your selected filters.')
        st.stop()

    revenue = filtered['revenue'].sum()
    profit = filtered['profit'].sum()
    transactions = filtered['transaction_id'].nunique()
    quantity = filtered['quantity'].sum()
    margin = 100 * profit / revenue if revenue else 0
    aov = revenue / transactions if transactions else 0

    row1 = st.columns(3, gap='medium')
    with row1[0]: metric('TOTAL REVENUE', compact(revenue, True), '#2563EB')
    with row1[1]: metric('TOTAL PROFIT', compact(profit, True), '#16A34A')
    with row1[2]: metric('PROFIT MARGIN', f'{margin:.2f}%', '#7C3AED')
    st.write('')
    row2 = st.columns(3, gap='medium')
    with row2[0]: metric('TRANSACTIONS', f'{transactions:,}', '#F59E0B')
    with row2[1]: metric('UNITS SOLD', f'{quantity:,}', '#0D9488')
    with row2[2]: metric('AVERAGE ORDER VALUE', compact(aov, True), '#4F46E5')

    monthly = filtered.groupby(pd.Grouper(key='full_date', freq='MS'))['revenue'].sum().reset_index()
    cats = filtered.groupby('category', as_index=False)['revenue'].sum().nlargest(8, 'revenue').sort_values('revenue')

    st.markdown('<div class="section-title">Business trends</div>', unsafe_allow_html=True)
    left, right = st.columns([1.3, 1], gap='large')
    with left:
        trend = go.Figure()
        trend.add_trace(go.Scatter(x=monthly['full_date'], y=monthly['revenue'], mode='lines+markers', line=dict(color='#2563EB', width=3), marker=dict(size=6), fill='tozeroy', fillcolor='rgba(37,99,235,0.08)', hovertemplate='%{x|%b %Y}<br>LKR %{y:,.0f}<extra></extra>'))
        trend = chart_style(trend, 'Monthly Revenue Trend')
        trend.update_yaxes(tickprefix='LKR ', tickformat='~s')
        st.plotly_chart(trend, use_container_width=True, config={'displayModeBar': False})
    with right:
        bar = go.Figure(go.Bar(x=cats['revenue'], y=cats['category'], orientation='h', marker_color='#7C3AED', hovertemplate='%{y}<br>LKR %{x:,.0f}<extra></extra>'))
        bar = chart_style(bar, 'Revenue by Category')
        bar.update_xaxes(tickprefix='LKR ', tickformat='~s')
        st.plotly_chart(bar, use_container_width=True, config={'displayModeBar': False})

    st.markdown('<div class="section-title">Store performance</div>', unsafe_allow_html=True)
    stores = filtered.groupby('store_name', as_index=False)[['revenue', 'profit']].sum().sort_values('revenue', ascending=False)
    st.dataframe(stores.rename(columns={'store_name': 'Store', 'revenue': 'Revenue (LKR)', 'profit': 'Profit (LKR)'}), use_container_width=True, hide_index=True)

elif page == "Sales Analytics":
    from sales_page import render_sales

    render_sales(
        get_engine,
        metric,
        chart_style
    )


elif page == "Inventory Intelligence":
    from inventory_page import render_inventory
    from inventory_forecast_page import render_inventory_forecast_risk
    from replenishment_page import render_replenishment_planning

    # Existing inventory analytics
    render_inventory(
        get_engine,
        metric,
        chart_style
    )

    st.divider()

    # Forecast-based inventory risk analysis
    render_inventory_forecast_risk(chart_style)

    st.divider()

    # Forecast-based replenishment planning
    render_replenishment_planning(chart_style)


elif page == "Customer Intelligence":
    from customer_page import render_customers

    render_customers(
        get_engine,
        metric,
        chart_style
    )


elif page == "Demand Forecasting":
    from demand_page import render_demand
    from forward_forecast_page import render_forward_forecasts

    # Interactive 7/14-day forecast explorer
    render_forward_forecasts(chart_style)

    st.divider()

    # Existing historical model evaluation
    render_demand(
        metric,
        chart_style
    )


else:
    st.info(
        "This workspace is next in development."
    )

st.caption('Retail Intelligence Platform · Synthetic data · For portfolio demonstration only')
