# Retail Sales & Inventory Intelligence Platform

**End-to-end retail analytics and decision-support portfolio project** combining a PostgreSQL dimensional warehouse, Python ETL, customer segmentation, demand forecasting, inventory-risk analysis, Streamlit, and Power BI.

[![Python CI](https://github.com/balakrishnanpremnath/retail-intelligence-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/balakrishnanpremnath/retail-intelligence-platform/actions/workflows/ci.yml)

> **Data disclosure:** This project uses **synthetically generated retail data** for demonstration and learning. Dashboards are local, not a hosted live service. Forecasts and inventory scenarios are **saved historical snapshots as of 30 September 2026**, not live predictions or purchase orders.

## Project overview

The platform demonstrates how retail transaction and inventory data can support a complete analytics workflow:

**Raw data → staging ETL → PostgreSQL star schema → analytics views and feature engineering → ML and forecasting → inventory decisions → Streamlit / Power BI**

The business questions addressed include:

- What drives revenue, profit, and performance across stores and product categories?
- Which customers have high value or may need re-engagement?
- How well do simple demand baselines compare with machine-learning models?
- Which store-product combinations may face shortages under a future-demand scenario?
- How might a transparent replenishment policy translate predictions into planning quantities?

## Dataset at a glance

| Dataset statistic | Value |
|---|---:|
| Transactions | 19,329 |
| Units sold | 46,418 |
| Products | 30 |
| Stores | 4 |
| Customers | 500 |
| Inventory snapshot rows | 120 |
| Transaction period | 1 Jan 2025 – 30 Sep 2026 |
| Total revenue | LKR 82,745,560.53 |
| Total profit | LKR 16,615,114.78 |
| Profit margin | 20.08% |

The four synthetic branches represent Colombo, Kandy, Galle, and Jaffna. Original input CSV files are in [`data/raw/`](data/raw/).

## Dashboards and analysis

| Workspace | What it shows |
|---|---|
| **Executive Overview** | Business KPIs, revenue trends, category and branch performance |
| **Sales Analytics** | Sales drilldowns and product/category insights |
| **Inventory Intelligence** | Stock health, reorder alerts, forecast-based stock risk, and 14-day replenishment scenarios |
| **Customer Intelligence** | RFM-based customer segmentation and customer profiles |
| **Demand Forecasting** | Historical model evaluation, saved recursive 7/14-day forecasts, model comparisons, and CSV downloads |

The interactive application uses Streamlit and Plotly with PostgreSQL analytics views. A separate Power BI report is in [`dashboard/Retail_Intelligence_Dashboard.pbix`](dashboard/Retail_Intelligence_Dashboard.pbix).

### Preview

| Executive overview | Inventory intelligence |
|---|---|
| ![Executive Overview](images/executive_overview.png) | ![Inventory Intelligence](images/inventory_intelligence.png) |
| **Sales analytics** | **Customer analytics** |
| ![Sales Analytics](images/sales_deep_dive.png) | ![Customer Analytics](images/customer_analytics.png) |

Additional forecast, inventory-risk, and replenishment screenshots can be added as the final portfolio presentation is completed.

## Machine learning and evaluation

### Customer segmentation

RFM (**Recency, Frequency, Monetary**) features and K-Means clustering were used to segment the 500 synthetic customers. The selected `k=3` achieved a **silhouette score of 0.3674** among the tested values. The resulting descriptive groups were **High Value (231)**, **Loyal (190)**, and **At Risk (79)** customers. These labels illustrate the method, not real customer behavior. See [`docs/customer_segmentation.md`](docs/customer_segmentation.md).

### Daily demand forecasting — 90-day evaluation

The final 90 days, **3 July – 30 September 2026**, were evaluated chronologically at the store-product-day level (**10,800 test observations**):

| Method | MAE (units) | RMSE (units) |
|---|---:|---:|
| Rolling 7-day average | **0.8619** | 1.4525 |
| Poisson regression | 0.8829 | **1.3756** |
| Random forest regression | 0.9197 | 1.3962 |

The rolling average had the lowest MAE; Poisson regression had the lowest RMSE. **A more complex model did not automatically outperform the baseline.** This comparison concerns one-step historical evaluation, not a 14-day forecast. Details: [`docs/model_evaluation.md`](docs/model_evaluation.md).

### Recursive 7/14-day forecasts

The platform also implements genuine recursive multi-step forecasting, where earlier predicted values feed later lag and rolling-window features. Historical rolling-origin evaluation was performed on folds before the final 90-day period:

| Method | 7-day mean RMSE | 14-day mean RMSE |
|---|---:|---:|
| Recursive Poisson | **1.3848** | **1.4468** |
| Recursive Rolling-7 | 1.4560 | 1.5123 |

On these multi-step folds, recursive Rolling-7 had lower MAE than recursive Poisson; recursive Poisson had lower RMSE. A zero-demand baseline obtained low MAE on sparse data but fails to capture actual positive demand, illustrating why a single metric is insufficient for business decisions.

Saved model forecasts cover **1–14 October 2026** using data through **30 September 2026**. They are archived forecasting demonstrations, not real-time predictions.

## From forecasting to inventory decisions

The platform joins saved Poisson demand forecasts to the matching synthetic stock snapshot, by store and product, to calculate scenario-based inventory risk.

| Measure (all stores) | 7-day scenario | 14-day scenario |
|---|---:|---:|
| Expected demand | 496.34 units | 982.85 units |
| Store-products with forecast demand gaps | 1 | 3 |
| Sum of rounded potential gaps | 1 unit | 15 units |

A separate **illustrative 14-day replenishment policy** takes the forecast demand, adds the existing reorder-level buffer, and subtracts available stock:

```text
planning_target_units = ceil(expected_14d_demand + reorder_level)
scenario_order_units = max(0, planning_target_units - stock_on_hand)
```

Its saved output has **3 urgent-review**, **31 plan-replenishment**, and **86 monitor** records, with **925 total scenario units**. **These 925 units are policy-based planning quantities, not forecast shortages.** The implementation suppresses automatic purchasing suggestions for zero-demand items below their reorder level and flags them for manual review instead.

**Limitations:** These scenarios assume no incoming replenishment, and do not model supplier lead times, minimum order quantities, procurement costs, service-level targets, forecast intervals, or uncertainty. Human review is required before any purchasing decision.

## Technology stack

**Data and analytics:** Python 3.12, Pandas, NumPy, SQL, PostgreSQL 16, SQLAlchemy  
**Modeling:** scikit-learn, RFM, K-Means, random forest, Poisson regression, statistical baselines  
**Visualization:** Streamlit, Plotly, Power BI  
**Delivery and quality:** Docker Compose, pytest, GitHub Actions CI

## Repository structure

```text
retail-intelligence-platform/
├── app/                   # Streamlit dashboards and interactive explorers
├── data/raw/              # Committed synthetic example datasets
├── data/processed/        # Locally generated analytical features
├── database/sql/          # Warehouse DDL, loading SQL, analytical views
├── dashboard/             # Power BI .pbix report
├── docs/                  # Methods, insights, evaluation, data dictionary
├── etl/                   # Data generation, feature engineering, loaders
├── images/                # Dashboard screenshots
├── models/                # Modeling code and selected saved CSV results
├── scripts/               # Safe database bootstrap and smoke tests
├── tests/                 # Automated unit and data-quality tests
├── .env.example           # Example local database configuration
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── requirements-app.txt
```

## Run locally (Windows PowerShell)

**Prerequisites:** Git, Python **3.12**, Docker Desktop with Docker Compose, and free local ports **5432** (PostgreSQL) and **8501** (Streamlit).

> These instructions initialize a **new** database. Do not use `--initialize` on an existing retail database; the bootstrap script detects application schemas and refuses to overwrite them. **Never use `docker compose down -v`** on a database containing data you want to keep.

**1. Clone the repository and configure credentials**

```powershell
git clone https://github.com/balakrishnanpremnath/retail-intelligence-platform.git
cd retail-intelligence-platform
Copy-Item .env.example .env
```

Edit `.env` if needed. Keep the credentials private and do not commit the file. In local host-side Python scripts, `POSTGRES_HOST=localhost` and `POSTGRES_PORT=5432`; Docker Compose supplies the internal hostname `postgres` to the Streamlit container.

**2. Install Python dependencies**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**3. Start PostgreSQL and initialize a new database**

```powershell
docker compose up -d postgres
.\.venv\Scripts\python.exe scripts\bootstrap_database.py
.\.venv\Scripts\python.exe scripts\bootstrap_database.py --initialize
```

Use `--initialize` **only** after the read-only check reports that no application schemas exist. This loads the committed sample staging data, creates the star schema and analytics tables, and builds the reporting views. The database is stored in a persistent Docker volume.

**4. Build and run Streamlit**

```powershell
docker compose up -d --build streamlit
docker compose ps
```

Open **http://localhost:8501**, then explore the five sidebar workspaces.

**5. Verify the system**

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe scripts\smoke_test.py
```

The smoke test checks Streamlit's health endpoint and the presence of records in four PostgreSQL analytics views. The full automated suite had **72 passing tests** at the latest locally verified checkpoint; future updates may change this number.

### Existing database or returning to the project

When the database is already initialized, **skip** `--initialize` and start your existing services:

```powershell
docker compose up -d
docker compose ps
```

The read-only `scripts/bootstrap_database.py` check is safe to run without the initialization flag. A healthy PostgreSQL container alone does not guarantee that the analytics tables are loaded; run the smoke test as well.

## Data freshness and reproducibility

- All datasets, sales figures, customer segments, model results, and planning quantities are **synthetic demonstration artifacts**; the project is not connected to a real retailer.
- The dashboard reads current values from a **local, populated PostgreSQL warehouse** and saved forecast/analysis CSV artifacts. It does not ingest live feeds or automatically retrain models.
- The safe bootstrap was tested against a **separate empty PostgreSQL 16 container**; 19,329 sales rows, 120 inventory rows, 500 customer-view rows, and 21 monthly-view rows were verified after initialization.
- Existing analytics documents were written at different project milestones; some older documents may describe an earlier feature scope. This README describes the currently implemented workflows.

## Detailed project notes

- [Business insights](docs/business_insights.md)
- [Data dictionary](docs/data_dictionary.md)
- [Customer segmentation](docs/customer_segmentation.md)
- [Inventory intelligence](docs/inventory_intelligence.md)
- [Demand forecasting evaluation](docs/model_evaluation.md)

## License

Released under the [MIT License](LICENSE).
