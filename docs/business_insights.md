# Business Insights — Retail Sales & Inventory Intelligence Platform

> **Data scope:** All figures are from a **synthetic Sri Lankan retail dataset**, not a real retailer. Sales cover **1 January 2025–30 September 2026**. Forecast and inventory-planning examples use the **30 September 2026** snapshot and are **not live operational advice**.

## Executive summary

The project analyzes 19,329 transactions covering 46,418 units sold across 30 products, 4 stores, and 500 customers. It combines SQL business analysis, customer segmentation, historical demand forecasting, inventory-risk estimates, and explainable replenishment scenarios.

| KPI | Synthetic dataset result |
|---|---:|
| Transactions | 19,329 |
| Units sold | 46,418 |
| Revenue | LKR 82,745,560.53 |
| Profit | LKR 16,615,114.78 |
| Profit margin | 20.08% |

## Revenue and profit drivers

### Highest-revenue products

| Product | Revenue (LKR) | Profit (LKR) |
|---|---:|---:|
| Cooking Oil 1L | 9,122,541.26 | 1,604,082.14 |
| Milk Powder 400g | 8,573,776.32 | 1,317,668.04 |
| Soft Drink 1.5L | 8,415,154.59 | 1,319,095.76 |
| Canned Fish | 4,802,618.61 | 1,227,937.49 |
| Cheese Pack | 4,406,055.94 | 1,046,475.14 |

**Interpretation:** The leading products deserve close sales and availability monitoring in this synthetic example. High revenue alone does not establish optimal margins, demand stability, or priority for capital allocation.

### Store performance

| Store | Revenue (LKR) | Profit (LKR) |
|---|---:|---:|
| Galle Town | 21,202,331.63 | 4,263,889.37 |
| Kandy City | 20,888,996.76 | 4,181,029.53 |
| Jaffna North | 20,342,799.04 | 4,102,773.58 |
| Colombo Central | 20,311,433.10 | 4,067,422.30 |

The four stores have relatively similar sales totals. Galle Town ranks first in this particular generated dataset.

### Promotion comparison

| Sale type | Revenue (LKR) | Profit margin |
|---|---:|---:|
| Promotion | 11,161,887.65 | 13.67% |
| No promotion | 71,583,672.88 | 21.08% |

The synthetic promotion group has a lower margin. This is **descriptive association**, not proof that promotions cause lower profitability or are ineffective; a causal analysis would need additional controls and business objectives.

## Customer intelligence

RFM features and K-Means produce three **descriptive** customer segments (best silhouette score among tested `k=2` to `k=6`: **0.3674**):

| Segment | Customers | Illustrative next action |
|---|---:|---|
| High Value | 231 | Consider loyalty recognition and retention |
| Loyal | 190 | Explore cross-selling and targeted offers |
| At Risk | 79 | Review re-engagement opportunities |

These are exploratory labels applied to synthetic customers, not measured campaign outcomes. See [Customer Segmentation](customer_segmentation.md).

## Forecasting: why baselines matter

On the **90-day chronological one-step evaluation** (10,800 store-product-day observations):

| Model | MAE ↓ | RMSE ↓ |
|---|---:|---:|
| Rolling 7-day average | **0.8619** | 1.4525 |
| Poisson regression | 0.8829 | **1.3756** |
| Random Forest | 0.9197 | 1.3962 |

The simple Rolling-7 baseline has the lowest MAE; Poisson has the lowest RMSE. Random Forest does not automatically improve on them. These metrics **must not** be mixed with the separate recursive 7/14-day backtest results. See [Model Evaluation](model_evaluation.md).

## Forecast-based inventory decisions

The platform combines saved recursive Poisson forecasts with the matching **30 September 2026** stock snapshot. Assuming no incoming deliveries:

| Inventory-risk metric | 7 days | 14 days |
|---|---:|---:|
| Expected demand | 496.34 units | 982.85 units |
| Store-products with projected demand gaps | 1 | 3 |
| Sum of individually rounded projected gaps | 1 unit | 15 units |
| Reorder-level risk, excluding demand gaps | 32 | 31 |

In the 14-day scenario, three store-product combinations have positive forecast coverage gaps:

| Store | Product | Stock | Expected 14-day demand | Rounded potential gap |
|---|---|---:|---:|---:|
| Galle Town | Rice 10kg | 7 | 10.495 | 4 |
| Kandy City | Milk Powder 400g | 5 | 11.266 | 7 |
| Jaffna North | Toothpaste 120g | 19 | 22.932 | 4 |

These represent **forecast-based risks**, not confirmed stockouts.

### Replenishment-planning scenario

An **illustrative 14-day policy** uses `ceil(expected_demand + reorder_level)` as its planning target, with suggested scenario units equal to `max(0, target - stock_on_hand)`. It generates:

| Planning action | Store-product records |
|---|---:|
| Urgent Review | 3 |
| Plan Replenishment | 31 |
| Monitor | 86 |
| Manual Review | 0 |
| **Total** | **120** |

The policy produces **925 total scenario units**. This is **not the same as** the **15 units of rounded forecast demand gaps**: the scenario quantity includes the additional reorder-level buffer. These are hypothetical quantities rather than purchase orders or proven savings.

## What a retailer could investigate next

1. Review products with projected demand gaps before making any replenishment decision.
2. Validate reorder levels and lead times with real supplier and stock records.
3. Compare demand forecasts against actual subsequent sales, and monitor forecast drift.
4. Evaluate promotions using profit, sales volume, customer response, and relevant controls.
5. Test retention strategies on genuine customer data before claiming an impact.

## Limitations and provenance

- **Synthetic data:** Insights illustrate methodology and should not be generalized to real Sri Lankan retailers.
- **Archived forecasts:** 1–14 October 2026 projections were produced as of 30 September 2026; the dashboard is not connected to a live feed.
- **No inventory simulation of deliveries:** Lead times, incoming shipments, purchasing costs, supplier minimums, demand uncertainty, and service-level targets are not modeled.
- **No causal or financial impact claim:** Neither sales uplift nor reductions in stockouts or purchasing expense have been experimentally demonstrated.
- **Methods and code:** See [`../models/`](../models/), [`../database/sql/`](../database/sql/), and the [root README](../README.md).
