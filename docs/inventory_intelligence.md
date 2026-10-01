\# Inventory Intelligence



\## Objective



The inventory intelligence component combines current stock levels with recent product demand to identify products that may require replenishment.



\## Inputs Used



The recommendation logic uses:



\- current stock on hand,

\- reorder level,

\- average daily demand from the last 30 days,

\- estimated days of stock cover,

\- projected 14-day demand,

\- safety stock.



\## Reorder Logic



\### URGENT



A product is classified as \*\*URGENT\*\* when estimated stock cover is 7 days or less.



These products require immediate attention.



\### REORDER



A product is classified as \*\*REORDER\*\* when:



\- stock is at or below the reorder level, or

\- estimated stock cover is 14 days or less.



A positive reorder quantity is automatically calculated.



\### REVIEW



A product is classified as \*\*REVIEW\*\* when:



\- stock is below the reorder level,

\- but no demand was recorded during the last 30 days.



Instead of automatically ordering more stock, manual review is recommended because the product may be slow-moving or inactive.



\### WATCH



A product is classified as \*\*WATCH\*\* when inventory is approaching the reorder threshold.



\### OK



A product is classified as \*\*OK\*\* when current inventory is considered healthy.



\## Target Stock Calculation



The system considers two targets:



1\. Demand-based target stock

2\. Inventory-policy target stock



The final target stock uses the higher of the two.



This prevents the system from recommending unrealistically low replenishment quantities.



\## Safety Stock



Seven days of recent average demand are used as a simple safety-stock buffer.



\## Recommended Reorder Quantity



Recommended reorder quantity is calculated as:



```text

Target Stock - Current Stock

