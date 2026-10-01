\# Customer Segmentation Analysis



\## Objective



The purpose of this analysis is to group customers based on their purchasing behaviour using RFM analysis and K-Means clustering.



RFM represents:



\- \*\*Recency\*\* — how many days since the customer's last purchase

\- \*\*Frequency\*\* — how many transactions the customer made

\- \*\*Monetary\*\* — how much revenue the customer generated



\## Selecting the Number of Clusters



K-Means models were evaluated using silhouette score.



| K | Silhouette Score |

|---:|---:|

| 2 | 0.3364 |

| 3 | \*\*0.3674\*\* |

| 4 | 0.3150 |

| 5 | 0.2785 |

| 6 | 0.2894 |



K=3 achieved the highest silhouette score among the tested values.



Therefore, three customer segments were selected.



\## Final Customer Segments



| Segment | Customers | Avg Recency | Avg Frequency | Avg Monetary Value |

|---|---:|---:|---:|---:|

| High Value | 231 | 11.97 days | 43.08 | LKR 191,423.01 |

| Loyal | 190 | 12.94 days | 33.39 | LKR 134,551.84 |

| At Risk | 79 | 48.87 days | 38.41 | LKR 164,075.90 |



\## Segment Interpretation



\### High Value



These customers purchase frequently, purchased recently, and generate the highest average revenue.



Recommended business actions:



\- loyalty rewards,

\- personalized offers,

\- early access to promotions,

\- retention campaigns.



\### Loyal



These customers purchase regularly and have recent activity, but their average spending is lower than the High Value group.



Recommended business actions:



\- cross-selling,

\- product recommendations,

\- loyalty-point incentives,

\- targeted bundles.



\### At Risk



These customers have historically purchased frequently and generated relatively high revenue, but their last purchase was much longer ago.



Recommended business actions:



\- re-engagement campaigns,

\- personalized discount offers,

\- reminder messages,

\- win-back promotions.



\## Key Business Insight



The At Risk segment is particularly important because these customers previously generated strong revenue but have recently become less active.



Recovering even part of this segment could provide more value than focusing only on acquiring new customers.



\## Methodology



The clustering process included:



1\. Creating Recency, Frequency and Monetary features.

2\. Applying log transformation to reduce skew in Frequency and Monetary values.

3\. Standardizing the features using StandardScaler.

4\. Testing K values from 2 to 6.

5\. Comparing silhouette scores.

6\. Selecting K=3.

7\. Profiling each cluster and assigning business-friendly segment names.



\## Limitation



The dataset used in this portfolio project is synthetically generated. Therefore, the customer segments demonstrate the analytical methodology rather than representing real customer behaviour.

