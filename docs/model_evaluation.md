\# Demand Forecasting Model Evaluation



\## Objective



The goal of the forecasting experiment was to predict daily product demand at the store-product level.



The final 90 days of the dataset were kept as an unseen test period to avoid time-series data leakage.



\## Data Split



\- Training period: 2025-01-15 to 2026-07-02

\- Testing period: 2026-07-03 to 2026-09-30

\- Training rows: 64,080

\- Testing rows: 10,800



\## Models Compared



Three forecasting approaches were evaluated:



1\. Rolling 7-Day Average Baseline

2\. Poisson Regression

3\. Random Forest Regression



\## Results



| Model | MAE | RMSE |

|---|---:|---:|

| Rolling 7-Day Baseline | 0.8619 | 1.4525 |

| Poisson Regression | 0.8829 | 1.3756 |

| Random Forest | 0.9197 | 1.3962 |



\## Interpretation



The Rolling 7-Day Average produced the lowest MAE.



This means that, on average, the simple rolling historical demand estimate produced smaller absolute forecasting errors than the machine-learning models.



Poisson Regression produced the lowest RMSE, indicating that it handled some larger prediction errors better than the other approaches.



Random Forest did not outperform the simpler approaches despite having greater model complexity.



\## Model Selection



MAE was selected as the primary business metric because it expresses forecasting error directly in units of product demand.



Based on MAE, the Rolling 7-Day Average is used as the current benchmark forecasting method.



Poisson Regression remains useful as a challenger model because it achieved the lowest RMSE.



\## Key Learning



A more complex machine-learning model is not automatically better than a simple baseline.



Comparing models against a strong baseline helps determine whether additional model complexity provides real business value.



\## Important Features



Random Forest feature importance showed that recent historical demand was highly informative.



The most important features included:



\- 28-day rolling average demand

\- 7-day rolling average demand

\- month

\- day of week

\- 14-day lag demand

\- 1-day lag demand

\- 7-day lag demand



This suggests that recent demand history and seasonal patterns are important predictors of future retail demand.

