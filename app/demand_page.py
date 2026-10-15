"""Demand forecasting evaluation page for Retail Intelligence Streamlit.

Shows historical, out-of-sample model evaluation on synthetic retail data.
Metrics are loaded from existing saved experiments, not calculated on live data.
"""

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


MODEL_DIR = Path(__file__).resolve().parents[1] / "models"
MODEL_COLORS = {
    "Rolling 7 Baseline": "#2563EB",
    "Poisson Regression": "#7C3AED",
    "Random Forest": "#F59E0B",
}
FEATURE_LABELS = {
    "rolling_28_avg": "28-day demand average",
    "rolling_7_avg": "7-day demand average",
    "lag_14_qty": "Demand 14 days ago",
    "lag_7_qty": "Demand 7 days ago",
    "lag_1_qty": "Demand yesterday",
    "day_of_week": "Day of week",
    "is_weekend": "Weekend indicator",
    "month": "Month",
    "quarter": "Quarter",
    "year": "Year",
}


@st.cache_data(ttl=300, show_spinner="Loading forecasting evaluation...")
def load_forecast_evaluation():
    """Load tracked experiment metrics and Random Forest feature importances."""
    leaderboard_path = MODEL_DIR / "model_leaderboard.csv"
    metrics_path = MODEL_DIR / "demand_metrics.json"
    importance_path = MODEL_DIR / "demand_feature_importance.csv"

    leaderboard = pd.read_csv(leaderboard_path)
    with metrics_path.open("r", encoding="utf-8") as file:
        metadata = json.load(file)
    importance = pd.read_csv(importance_path)

    required_leaderboard = {"Model", "MAE", "RMSE"}
    required_importance = {"feature", "importance"}
    if not required_leaderboard.issubset(leaderboard.columns):
        raise ValueError("Missing required model leaderboard columns")
    if not required_importance.issubset(importance.columns):
        raise ValueError("Missing required feature importance columns")

    leaderboard["MAE"] = pd.to_numeric(leaderboard["MAE"], errors="raise")
    leaderboard["RMSE"] = pd.to_numeric(leaderboard["RMSE"], errors="raise")
    importance["importance"] = pd.to_numeric(importance["importance"], errors="raise")
    if leaderboard.empty or (leaderboard[["MAE", "RMSE"]] < 0).any().any():
        raise ValueError("Leaderboard is empty or has invalid error metrics")
    if importance.empty:
        raise ValueError("No feature importance rows available")

    # The exported leaderboard already has a Rank column. Recompute after sorting.
    leaderboard = leaderboard.drop(columns=["Rank"], errors="ignore")
    leaderboard = leaderboard.sort_values("MAE").reset_index(drop=True)
    leaderboard.insert(0, "Rank", leaderboard.index + 1)
    importance = importance.sort_values("importance", ascending=False)
    return leaderboard, metadata, importance


def readable_feature(name):
    """Readable labels for scikit-learn transformed feature names."""
    name = str(name)
    if name.startswith("numeric__"):
        key = name.removeprefix("numeric__")
        return FEATURE_LABELS.get(key, key.replace("_", " ").title())
    return name.removeprefix("categorical__").replace("_", " ")


def metric_bar_chart(data, metric_name, chart_style):
    """Horizontal comparison; lower prediction error is better."""
    ordered = data.sort_values(metric_name, ascending=False)
    colors = [MODEL_COLORS.get(name, "#64748B") for name in ordered["Model"]]
    values = ordered[metric_name]
    fig = go.Figure(go.Bar(
        x=values,
        y=ordered["Model"],
        orientation="h",
        marker_color=colors,
        text=values.map(lambda x: f"{x:.4f}"),
        textposition="outside",
        hovertemplate="%{y}<br>" + metric_name + ": %{x:.4f} units<extra></extra>",
    ))
    chart_style(fig, f"Model Comparison — {metric_name}")
    fig.update_layout(
        height=340,
        margin=dict(l=15, r=64, t=60, b=45),
        xaxis_title="Error (daily units per store-product)",
        yaxis_title=None,
    )
    fig.update_xaxes(range=[0, max(values) * 1.25])
    return fig


@st.cache_data(ttl=300, show_spinner=False)
def load_rf_backtest():
    """Optional locally saved Random Forest holdout predictions (ignored by Git)."""
    path = MODEL_DIR / "demand_test_predictions.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path, parse_dates=["date"])
    required = {"date", "store_id", "product_name", "quantity", "predicted_quantity"}
    if not required.issubset(df.columns):
        raise ValueError("Random Forest predictions CSV has unexpected columns")
    return df


def render_demand(metric, chart_style):
    """Premium forecasting dashboard from verified historical model artifacts."""
    try:
        leaderboard, run_info, importance = load_forecast_evaluation()
    except (FileNotFoundError, ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        st.error("Cannot load saved forecasting evaluation files from the models folder.")
        st.caption(f"Details: {exc}")
        st.stop()

    st.caption(
        "Synthetic retail demand · Historical out-of-sample evaluation · "
        "No live forecast is being generated on this page"
    )

    best_mae = leaderboard.loc[leaderboard["MAE"].idxmin()]
    best_rmse = leaderboard.loc[leaderboard["RMSE"].idxmin()]
    test_start = pd.Timestamp(run_info["testing_start"])
    test_end = pd.Timestamp(run_info["testing_end"])
    test_days = (test_end - test_start).days + 1

    st.markdown('<div class="section-title">Forecasting performance at a glance</div>', unsafe_allow_html=True)
    tiles = [
        ("MODELS COMPARED", f"{len(leaderboard)}", "#2563EB"),
        ("BEST MAE", f"{best_mae['MAE']:.4f} units", "#16A34A"),
        ("BEST RMSE", f"{best_rmse['RMSE']:.4f} units", "#7C3AED"),
        ("TEST OBSERVATIONS", f"{int(run_info['testing_rows']):,}", "#EA580C"),
        ("HOLDOUT PERIOD", f"{test_days} days", "#0D9488"),
        ("BEST BY MAE", "Rolling 7-Day" if best_mae["Model"] == "Rolling 7 Baseline" else str(best_mae["Model"]), "#4F46E5"),
    ]
    for start in (0, 3):
        cols = st.columns(3, gap="medium")
        for col, (title, value, color) in zip(cols, tiles[start:start + 3]):
            with col:
                metric(title, value, color)
        st.write("")

    st.info(
        f"**MAE champion: {best_mae['Model']}** ({best_mae['MAE']:.4f} units). "
        f"**RMSE champion: {best_rmse['Model']}** ({best_rmse['RMSE']:.4f} units). "
        "Lower is better. MAE is the primary business selection metric."
    )

    st.markdown('<div class="section-title">Model comparison</div>', unsafe_allow_html=True)
    col_mae, col_rmse = st.columns(2, gap="large")
    with col_mae:
        st.plotly_chart(
            metric_bar_chart(leaderboard, "MAE", chart_style),
            use_container_width=True,
            config={"displayModeBar": False},
        )
    with col_rmse:
        st.plotly_chart(
            metric_bar_chart(leaderboard, "RMSE", chart_style),
            use_container_width=True,
            config={"displayModeBar": False},
        )

    st.markdown('<div class="section-title">Model leaderboard</div>', unsafe_allow_html=True)
    st.dataframe(
        leaderboard,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Rank": st.column_config.NumberColumn(format="%d"),
            "MAE": st.column_config.NumberColumn(format="%.4f"),
            "RMSE": st.column_config.NumberColumn(format="%.4f"),
        },
    )
    st.download_button(
        "Download model leaderboard CSV",
        data=leaderboard.to_csv(index=False),
        file_name="model_leaderboard.csv",
        mime="text/csv",
    )

    st.markdown('<div class="section-title">Feature importance & evaluation methodology</div>', unsafe_allow_html=True)
    col_features, col_notes = st.columns([1.25, 1], gap="large")
    with col_features:
        top = importance.head(10).copy()
        top["label"] = top["feature"].map(readable_feature)
        top = top.sort_values("importance", ascending=True)
        fig = go.Figure(go.Bar(
            x=top["importance"] * 100,
            y=top["label"],
            orientation="h",
            marker_color="#7C3AED",
            hovertemplate="%{y}: %{x:.2f}%<extra></extra>",
        ))
        chart_style(fig, "Random Forest — Top Feature Importances")
        fig.update_layout(
            height=420,
            margin=dict(l=20, r=20, t=60, b=45),
            xaxis_title="Share of total RF importance (%)",
            yaxis_title=None,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.caption("Feature importance is from Random Forest only, not the Rolling 7-Day baseline.")
    with col_notes:
        st.markdown("**Experiment setup**")
        st.write(f"Training: {run_info['training_start']} to {run_info['training_end']}")
        st.write(f"Holdout: {run_info['testing_start']} to {run_info['testing_end']}")
        st.write(f"Training observations: {int(run_info['training_rows']):,}")
        st.write(f"Testing observations: {int(run_info['testing_rows']):,}")
        st.markdown("**Why choose the baseline?**")
        st.write(
            "The 7-day rolling average has the lowest average absolute error. "
            "Poisson has the lowest RMSE. Model complexity did not translate "
            "to lower MAE on this synthetic holdout."
        )
        st.markdown("**How to interpret the errors**")
        st.write(
            "Errors are measured in daily units sold for each store-product pair. "
            "These are historical test-set results, not proof of performance "
            "on future real-world retail demand."
        )

    st.markdown('<div class="section-title">Optional historical predictions explorer</div>', unsafe_allow_html=True)
    try:
        predictions = load_rf_backtest()
    except (ValueError, OSError) as exc:
        st.warning(f"Saved Random Forest prediction file could not be read: {exc}")
        predictions = None

    if predictions is None:
        st.info(
            "Optional Random Forest prediction CSV is not present locally. "
            "The model leaderboard and feature charts above are complete. "
            "To recreate the optional backtest chart, run "
            "`python models/train_demand_model.py` after feature engineering."
        )
    else:
        st.caption("Random Forest historical test predictions only — not a forward-looking demand forecast.")
        c1, c2 = st.columns(2)
        with c1:
            store = st.selectbox("Store ID", ["All"] + sorted(predictions["store_id"].dropna().unique().tolist()), key="forecast_store")
        with c2:
            product = st.selectbox("Product", ["All"] + sorted(predictions["product_name"].dropna().unique().tolist()), key="forecast_product")
        view = predictions.copy()
        if store != "All":
            view = view[view["store_id"] == store]
        if product != "All":
            view = view[view["product_name"] == product]
        if view.empty:
            st.warning("No historical predictions match these filters.")
        else:
            view = view[view["date"] >= view["date"].max() - pd.Timedelta(days=29)]
            by_day = view.groupby("date", as_index=False)[["quantity", "predicted_quantity"]].sum()
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=by_day["date"], y=by_day["quantity"],
                mode="lines+markers", name="Actual sales", line=dict(color="#2563EB", width=3),
            ))
            fig.add_trace(go.Scatter(
                x=by_day["date"], y=by_day["predicted_quantity"],
                mode="lines+markers", name="Random Forest prediction",
                line=dict(color="#F59E0B", width=3, dash="dash"),
            ))
            chart_style(fig, "Historical Actual vs Random Forest Predicted Units — Last 30 Test Days")
            fig.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.2), height=400)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            st.caption("Daily quantities are summed across the chosen store and product selections.")

    st.caption(
        "Methodology: synthetic data, chronological holdout, 90 days, "
        "and saved experiment artifacts from the models folder. "
        "This dashboard does not retrain or deploy the forecasting models."
    )
