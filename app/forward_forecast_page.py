
"""Interactive future demand forecasts from saved model artifacts."""

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "models"

FORECAST_FILES = {
    "Recursive Poisson": "recursive_poisson_14day_forecasts.csv",
    "Recursive Rolling-7": "recursive_14day_forecasts.csv",
}

COLORS = {
    "Recursive Poisson": "#7C3AED",
    "Recursive Rolling-7": "#2563EB",
}


@st.cache_data(ttl=300)
def load_forward_forecasts():
    """Load and validate previously generated forecast snapshots."""

    frames = []

    for model_name, filename in FORECAST_FILES.items():
        path = MODEL_DIR / filename

        df = pd.read_csv(
            path,
            parse_dates=["as_of_date", "date"],
        )

        required = {
            "as_of_date",
            "date",
            "horizon_day",
            "store_id",
            "product_id",
            "product_name",
            "category",
            "forecast_quantity",
        }

        if not required.issubset(df.columns):
            raise ValueError(f"Missing columns in {filename}")

        df = df.copy()
        df["model"] = model_name
        df["forecast_quantity"] = pd.to_numeric(
            df["forecast_quantity"], errors="raise"
        )

        if (
            df.empty
            or not np.isfinite(df["forecast_quantity"]).all()
            or (df["forecast_quantity"] < 0).any()
        ):
            raise ValueError(f"Invalid quantities in {filename}")

        if df.duplicated(
            ["date", "store_id", "product_id"]
        ).any():
            raise ValueError(f"Duplicate forecasts in {filename}")

        frames.append(df)

    forecasts = pd.concat(frames, ignore_index=True)

    if forecasts["as_of_date"].nunique() != 1:
        raise ValueError("Model snapshots use different cutoff dates")

    expected_dates = (
        forecasts["as_of_date"]
        + pd.to_timedelta(forecasts["horizon_day"], unit="D")
    )

    if not forecasts["date"].eq(expected_dates).all():
        raise ValueError("Forecast dates and horizon days disagree")

    return forecasts


@st.cache_data(ttl=300)
def load_multistep_summary():
    path = MODEL_DIR / "recursive_poisson_cv_summary.csv"
    return pd.read_csv(path)


def render_forward_forecasts(chart_style):
    """Render interactive, saved 7/14-day forecast comparisons."""

    st.markdown(
        '<div class="section-title">'
        'Forward Demand Forecast Explorer'
        '</div>',
        unsafe_allow_html=True,
    )

    try:
        forecasts = load_forward_forecasts()
    except (OSError, ValueError, KeyError) as exc:
        st.warning(
            "Saved future forecasts are unavailable. "
            "Generate both recursive forecast CSV files first."
        )
        st.caption(str(exc))
        return

    as_of = forecasts["as_of_date"].iloc[0]

    st.info(
        f"**Forecast snapshot:** {as_of:%d %B %Y} | "
        "Synthetic retail dataset | "
        "Historical saved predictions, not live forecasts."
    )

    stores = sorted(forecasts["store_id"].unique())

    c1, c2, c3 = st.columns(3)

    with c1:
        store = st.selectbox(
            "Select Store",
            stores,
            key="forward_store",
        )

    store_data = forecasts[
        forecasts["store_id"] == store
    ]

    products = (
        store_data[["product_id", "product_name"]]
        .drop_duplicates()
        .sort_values("product_name")
    )

    product_labels = dict(zip(
        products["product_id"],
        products["product_name"],
    ))

    with c2:
        product_id = st.selectbox(
            "Select Product",
            products["product_id"].tolist(),
            format_func=lambda p: product_labels[p],
            key="forward_product",
        )

    with c3:
        horizon = st.selectbox(
            "Forecast Horizon",
            [7, 14],
            format_func=lambda d: f"{d} days",
            key="forward_horizon",
        )

    selected = forecasts[
        (forecasts["store_id"] == store)
        & (forecasts["product_id"] == product_id)
        & (forecasts["horizon_day"] <= horizon)
    ].copy()

    if selected.empty:
        st.warning("No forecast available for this selection.")
        return

    totals = (
        selected.groupby("model")["forecast_quantity"]
        .sum()
        .to_dict()
    )

    poisson_total = totals.get("Recursive Poisson", 0)
    rolling_total = totals.get("Recursive Rolling-7", 0)

    m1, m2, m3 = st.columns(3)

    with m1:
        st.metric(
            "Poisson Expected Demand",
            f"{poisson_total:.1f} units",
        )

    with m2:
        st.metric(
            "Rolling-7 Expected Demand",
            f"{rolling_total:.1f} units",
        )

    with m3:
        st.metric(
            "Poisson vs Rolling-7",
            f"{poisson_total - rolling_total:+.1f} units",
        )

    fig = go.Figure()

    for name in FORECAST_FILES:
        view = selected[
            selected["model"] == name
        ].sort_values("date")

        fig.add_trace(go.Scatter(
            x=view["date"],
            y=view["forecast_quantity"],
            name=name,
            mode="lines+markers",
            line=dict(
                color=COLORS[name],
                width=3,
            ),
            hovertemplate=(
                "%{x|%d %b %Y}"
                "<br>Expected units: %{y:.3f}"
                "<extra></extra>"
            ),
        ))

    chart_style(
        fig,
        f"{horizon}-Day Demand Forecast — "
        f"{product_labels[product_id]}",
    )

    fig.update_layout(
        height=420,
        showlegend=True,
        legend=dict(orientation="h", y=-0.25),
        yaxis_title="Expected units per day",
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={"displayModeBar": False},
    )

    st.caption(
        "Forecast values represent expected demand and may be "
        "fractional. Daily forecasts are not guaranteed sales."
    )

    st.markdown(
        '<div class="section-title">'
        'Historical Multi-Step Backtest Comparison'
        '</div>',
        unsafe_allow_html=True,
    )

    try:
        summary = load_multistep_summary()
        summary = summary[
            summary["horizon_days"] == horizon
        ].sort_values("mean_rmse")

        st.dataframe(
            summary.round(4),
            use_container_width=True,
            hide_index=True,
        )

        st.caption(
            "Lower RMSE and MAE are better. "
            "These backtests use historical validation folds "
            "before the final 90-day holdout."
        )

    except (OSError, ValueError, KeyError) as exc:
        st.warning(f"Backtest summary unavailable: {exc}")

    export = selected[
        [
            "date",
            "store_id",
            "product_id",
            "model",
            "forecast_quantity",
        ]
    ].sort_values(["model", "date"])

    st.download_button(
        "Download Selected Forecasts CSV",
        data=export.to_csv(index=False),
        file_name=f"forecast_{store}_{product_id}_{horizon}days.csv",
        mime="text/csv",
    )
