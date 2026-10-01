\# Data Dictionary



This document explains the raw datasets used in the Retail Sales \& Inventory Intelligence Platform.



\## 1. products.csv



Contains product-level information.



| Column | Description |

|---|---|

| `product\_id` | Unique product identifier |

| `product\_name` | Name of the product |

| `category` | Product category |

| `unit\_cost` | Cost paid by the retailer for one unit |

| `unit\_price` | Selling price of one unit |

| `reorder\_level` | Minimum recommended inventory level before restocking |



\## 2. stores.csv



Contains information about retail branches.



| Column | Description |

|---|---|

| `store\_id` | Unique store identifier |

| `store\_name` | Store or branch name |

| `region` | Geographic region of the store |



\## 3. customers.csv



Contains customer information.



| Column | Description |

|---|---|

| `customer\_id` | Unique customer identifier |

| `customer\_name` | Customer name used in the synthetic dataset |

| `customer\_type` | Customer group: Retail, Loyalty, or Wholesale |

| `join\_date` | Date the customer joined the business |



\## 4. sales.csv



Contains individual retail sales transactions.



| Column | Description |

|---|---|

| `transaction\_id` | Unique transaction identifier |

| `date` | Date of the transaction |

| `store\_id` | Store where the transaction occurred |

| `customer\_id` | Customer involved in the transaction |

| `product\_id` | Product purchased |

| `quantity` | Number of units sold |

| `unit\_price` | Selling price per unit |

| `unit\_cost` | Cost per unit |

| `discount\_pct` | Discount percentage applied to the sale |

| `revenue` | Total sales revenue after discount |

| `cost` | Total cost of the products sold |

| `profit` | Revenue minus cost |

| `promotion` | Indicates whether the transaction was promotional |



\## 5. inventory.csv



Contains the latest inventory position for every product and store.



| Column | Description |

|---|---|

| `store\_id` | Store identifier |

| `product\_id` | Product identifier |

| `snapshot\_date` | Date of the inventory snapshot |

| `stock\_on\_hand` | Current available stock |

| `reorder\_level` | Minimum stock level before replenishment is recommended |



\## Dataset Summary



The dataset represents a synthetic multi-branch retail business and is designed for:



\- sales analysis,

\- profitability analysis,

\- inventory monitoring,

\- customer segmentation,

\- demand forecasting,

\- SQL analysis,

\- Power BI dashboards,

\- machine learning.

