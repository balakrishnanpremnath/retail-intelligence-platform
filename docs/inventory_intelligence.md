# Inventory Intelligence — Rules, Forecast Risk, and Replenishment Scenarios

> **Important:** Inventory values are synthetic snapshots dated **30 September 2026**. Forecast horizons extend to **7 or 14 days after that snapshot**. This document describes a reproducible demonstration, **not** real-time stock monitoring, confirmed shortages, or automatically approved purchase orders.

## Purpose and data sources

The Streamlit **Inventory Intelligence** workspace combines **three complementary methods**. Their statuses and recommended quantities are based on **different rules** and must not be treated as interchangeable.

| Component | Core input | Code / saved artifact |
|---|---|---|
| Recent-demand reorder rules | Stock, reorder levels, sales over the previous 30 days | [`models/build_reorder_recommendations.py`](../models/build_reorder_recommendations.py), `models/reorder_recommendations.csv` |
| Forecast-based inventory risk | Saved recursive Poisson forecasts plus matching stock snapshot | [`models/forecast_inventory_risk.py`](../models/forecast_inventory_risk.py), `models/forecast_inventory_risk.csv` |
| Replenishment-planning scenarios | 14-day forecast-risk output and existing reorder levels | [`models/replenishment_scenarios.py`](../models/replenishment_scenarios.py), `models/replenishment_scenarios.csv` |

All operations use the **store-product** grain. A record is one product in one store, not a unique product across the entire business. There are **120 combinations** (4 stores × 30 products).

## 1. Recent-demand inventory rules

Feature engineering calculates **average daily demand over the last 30 days** and **estimated stock cover** (`stock_on_hand / avg_daily_demand_30d`; undefined when demand is zero).

The rule-based target uses:

```text
forecast_14d_demand = avg_daily_demand_30d * 14
safety_stock        = avg_daily_demand_30d * 7
demand_target       = forecast_14d_demand + safety_stock
policy_target       = reorder_level + safety_stock
target_stock        = max(demand_target, policy_target)
recommended_qty     = max(0, ceil(target_stock - stock_on_hand))
```

Rules are applied in this priority order:

| Rule | When it applies | Action |
|---|---|---|
| URGENT | Positive recent demand; stock cover ≤ 7 days | Prioritize review and replenishment |
| REORDER | Positive recent demand; stock ≤ reorder level **or** cover ≤ 14 days | Review reorder recommendation |
| REVIEW | No recent demand and stock ≤ reorder level | **Manual review**; automatic order quantity set to zero |
| WATCH | Positive recent demand and stock ≤ 1.25 × reorder level | Monitor approaching threshold |
| OK | None of the above | No immediate rule-based action |

These thresholds are **demonstration rules**, not optimized supply-chain parameters. In particular, seven days of average demand is an assumed buffer, not a statistically estimated safety-stock requirement.

The inventory dashboard displays these rule-based results from PostgreSQL view `analytics.vw_inventory_intelligence`.

## 2. Forecast-based inventory risk

This analysis sums saved **recursive Poisson daily expected demand** for days 1–7 or 1–14, from the archived cutoff **30 September 2026**. The warehouse/CSV inventory snapshot must match the model cutoff date.

```text
expected_demand          = sum(daily Poisson forecasts over horizon)
projected_net_stock      = stock_on_hand - expected_demand
expected_coverage_gap    = ceil(max(0, -projected_net_stock))
```

Risk classification prioritizes:

1. **EXPECTED DEMAND GAP** — projected net stock is negative.
2. **REORDER LEVEL RISK** — projected net stock is nonnegative but at or below the reorder level.
3. **ADEQUATE BY POLICY** — projected net stock remains above the reorder level.

| Outcome across 120 store-products | 7-day horizon | 14-day horizon |
|---|---:|---:|
| Expected demand | 496.34 units | 982.85 units |
| ADEQUATE BY POLICY | 87 | 86 |
| REORDER LEVEL RISK | 32 | 31 |
| EXPECTED DEMAND GAP | 1 | 3 |
| Sum of rounded potential gap units | 1 | 15 |

For the **14-day** snapshot, the projected demand gaps are:

| Store | Product | Current stock | Expected demand | Rounded gap |
|---|---|---:|---:|---:|
| Galle Town | Rice 10kg | 7 | 10.495 | 4 |
| Kandy City | Milk Powder 400g | 5 | 11.266 | 7 |
| Jaffna North | Toothpaste 120g | 19 | 22.932 | 4 |

Fractional expected demand represents a model estimate; rounded gap units are useful for displaying whole-product units. **No deliveries or ordering events are assumed during the forecast window**, so these numbers are a simplified planning scenario rather than observed stockouts.

## 3. Explainable 14-day replenishment planning

The replenishment scenario uses the 14-day risk results but adds an explicit policy buffer:

```text
planning_target_units = ceil(expected_14d_demand + reorder_level)
scenario_order_units  = max(0, planning_target_units - stock_on_hand)
forecast_gap_units    = ceil(max(0, expected_14d_demand - stock_on_hand))
```

An item is flagged as **URGENT REVIEW** when forecast demand exceeds available stock; as **PLAN REPLENISHMENT** when forecast demand is covered but the planning target is not; otherwise **MONITOR**. If forecast demand is zero and stock is **below** reorder level, the system flags **MANUAL REVIEW** and sets scenario order quantity to zero. Actions are for *human review*, not automated procurement.

| Action | Records |
|---|---:|
| URGENT REVIEW | 3 |
| PLAN REPLENISHMENT | 31 |
| MONITOR | 86 |
| MANUAL REVIEW | 0 |
| **Total** | **120** |

The resulting **925 scenario order units** are **not** the same as the **15 rounded potential demand-gap units**. The larger number includes the reorder-level buffer and is not an estimated actual shortage, optimal order size, or committed purchase.

## Validation and reproducibility

- Forecast dates must match `as_of_date + horizon_day`, and input snapshot dates must align.
- Products must match on `(store_id, product_id)` without duplication; complete daily horizons are required.
- Stock and demand quantities must be finite and nonnegative.
- Unit tests cover scenario math, classifications, mismatches, duplicates, invalid input, and non-mutation of input DataFrames.
- The Streamlit dashboards offer store/category or action filters and CSV export of the saved scenario data.

Run the current automated test suite from the project root:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

## Limitations and next steps

Supplier lead times, confirmed incoming stock, supplier constraints, minimum order quantities, product shelf life, purchase prices, uncertainty intervals, business service-level targets, and operational feedback loops are **not modeled**. All results come from **synthetic, archived data**. Before deployment with real inventory, the policy would require validation against actual supply-chain processes and outcomes.

See the [project README](../README.md), [business insights](business_insights.md), and saved results in [`../models/`](../models/).
