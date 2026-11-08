# Retail Sales & Customer Analytics

I wanted to practice answering real business questions with SQL and Python. This project looks at two years of sales (2024-2025) for six Denver-area retail stores: about 62,000 orders and 6,000 customers.

**Note:** The data is made up. I wrote `generate_data.py` to create it, and I built in realistic patterns like holiday sales spikes, loyalty members shopping more, and different return rates for each category.

## Questions I answered

- How did sales change from 2024 to 2025?
- Which categories get returned the most, and why?
- Do big discounts actually help?
- Are loyalty members worth more than other customers?
- Which stores do the best?
- What are the busiest days of the week?

## What I found

- **Sales went up 5.5%**, from $2.80M in 2024 to $2.95M in 2025. November and December made up about a quarter of the year's sales.
- **Shoes and women's clothing get returned the most.** "Wrong size" was the main reason for about half of those returns, so better size charts could help.
- **Big discounts hurt profit.** Profit margin drops from 45% at full price to only 8% at 40% off, and those items get returned more often too.
- **Loyalty members matter a lot.** They're 39% of customers but bring in 55% of sales, mostly because they shop about twice as often.
- **Weekends are the busiest.** Saturday has about 70% more orders than Tuesday, so stores should have more staff on weekends.
- **The Denver Colfax store does the best**, both in total sales and sales per square foot.

## Customer groups

I used RFM (how recently, how often, and how much each customer spends) and K-Means clustering to split customers into 3 groups:

| Group | Customers | Share of sales |
|---|---|---|
| Champions | 1,864 | 68% |
| Loyal regulars | 2,300 | 28% |
| At risk (haven't shopped in about 8 months) | 1,364 | 4% |

The "at risk" group would be a good target for a "we miss you" coupon.

## Charts

![Monthly revenue](charts/monthly_revenue.png)
![Category returns](charts/category_returns.png)
![Discount vs margin](charts/discount_margin.png)
![Revenue concentration](charts/revenue_concentration.png)
![Customer segments](charts/customer_segments.png)

## Files

- `generate_data.py` - creates the fake sales data and saves it to a SQLite database
- `sql/schema.sql` - creates the tables
- `sql/analysis.sql` - the SQL queries I used to answer my questions
- `analysis.py` - runs the queries, makes the charts, and groups the customers

## How to run

```
pip install -r requirements.txt
python generate_data.py
python analysis.py
```

## Tools

SQL (SQLite), Python (pandas, scikit-learn, matplotlib)