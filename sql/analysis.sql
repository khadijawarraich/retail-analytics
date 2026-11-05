-- analysis.sql

-- name: q1_monthly_revenue
-- Q1. What does monthly revenue look like, and how does it compare to the same month last year?
WITH monthly AS (
    SELECT yr_month,
           ROUND(SUM(revenue), 2)              AS revenue,
           COUNT(DISTINCT order_id)            AS orders
    FROM v_sales
    WHERE is_returned = 0
    GROUP BY yr_month
)
SELECT yr_month,
       revenue,
       orders,
       LAG(revenue, 12) OVER (ORDER BY yr_month) AS revenue_last_year,
       ROUND(100.0 * (revenue - LAG(revenue, 12) OVER (ORDER BY yr_month))
             / LAG(revenue, 12) OVER (ORDER BY yr_month), 1) AS yoy_growth_pct
FROM monthly
ORDER BY yr_month;

-- name: q2_category_performance
-- Q2. Which categories drive revenue and margin, and which lose the most to returns?
SELECT category,
       ROUND(SUM(revenue), 0)                                         AS gross_revenue,
       ROUND(SUM(CASE WHEN is_returned = 1 THEN revenue ELSE 0 END), 0) AS returned_revenue,
       ROUND(100.0 * AVG(is_returned), 1)                             AS return_rate_pct,
       ROUND(100.0 * SUM(CASE WHEN is_returned = 0 THEN revenue - cost ELSE 0 END)
             / SUM(CASE WHEN is_returned = 0 THEN revenue ELSE 0 END), 1) AS net_margin_pct
FROM v_sales
GROUP BY category
ORDER BY gross_revenue DESC;

-- name: q3_store_ranking
-- Q3. How do stores rank on net revenue, revenue per square foot, and average basket?
WITH store_totals AS (
    SELECT s.store_name,
           s.sq_ft,
           SUM(CASE WHEN v.is_returned = 0 THEN v.revenue ELSE 0 END) AS net_revenue,
           COUNT(DISTINCT v.order_id)                                AS orders
    FROM v_sales v
    JOIN stores s ON s.store_id = v.store_id
    WHERE v.yr = '2025'
    GROUP BY s.store_name, s.sq_ft
)
SELECT store_name,
       ROUND(net_revenue, 0)                    AS net_revenue_2025,
       ROUND(net_revenue / sq_ft, 2)            AS revenue_per_sq_ft,
       ROUND(net_revenue / orders, 2)           AS avg_basket,
       RANK() OVER (ORDER BY net_revenue DESC)  AS revenue_rank,
       RANK() OVER (ORDER BY net_revenue / sq_ft DESC) AS efficiency_rank
FROM store_totals
ORDER BY revenue_rank;

-- name: q4_loyalty_vs_nonloyalty
-- Q4. Are loyalty members actually worth more than other customers?
WITH cust AS (
    SELECT c.customer_id,
           c.loyalty_member,
           COUNT(DISTINCT v.order_id)                                    AS orders,
           SUM(CASE WHEN v.is_returned = 0 THEN v.revenue ELSE 0 END)    AS net_spend
    FROM customers c
    JOIN v_sales v ON v.customer_id = c.customer_id
    GROUP BY c.customer_id, c.loyalty_member
)
SELECT CASE loyalty_member WHEN 1 THEN 'Loyalty member' ELSE 'Non-member' END AS segment,
       COUNT(*)                               AS customers,
       ROUND(AVG(orders), 1)                  AS avg_orders_2yr,
       ROUND(AVG(net_spend), 2)               AS avg_spend_2yr,
       ROUND(SUM(net_spend) / SUM(orders), 2) AS avg_order_value,
       ROUND(100.0 * SUM(net_spend) / (SELECT SUM(net_spend) FROM cust), 1) AS share_of_revenue_pct
FROM cust
GROUP BY loyalty_member;

-- name: q5_discount_impact
-- Q5. Do deeper discounts bring in bigger baskets, and what do they cost in margin and returns?
SELECT CASE WHEN discount_pct = 0 THEN '0% (full price)'
            ELSE CAST(CAST(discount_pct * 100 AS INTEGER) AS TEXT) || '%' END AS discount,
       COUNT(*)                                  AS line_items,
       ROUND(100.0 * AVG(is_returned), 1)        AS return_rate_pct,
       ROUND(100.0 * SUM(revenue - cost) / SUM(revenue), 1) AS margin_pct
FROM v_sales
GROUP BY discount_pct
ORDER BY discount_pct;

-- name: q6_return_reasons
-- Q6. Why do customers return items, by category? (top reason per category)
WITH reason_counts AS (
    SELECT p.category, r.reason, COUNT(*) AS n
    FROM returns r
    JOIN order_items oi ON oi.item_id = r.item_id
    JOIN products p     ON p.product_id = oi.product_id
    GROUP BY p.category, r.reason
),
ranked AS (
    SELECT category, reason, n,
           ROUND(100.0 * n / SUM(n) OVER (PARTITION BY category), 1) AS pct_of_category_returns,
           ROW_NUMBER() OVER (PARTITION BY category ORDER BY n DESC) AS rn
    FROM reason_counts
)
SELECT category, reason AS top_reason, n AS returns, pct_of_category_returns
FROM ranked
WHERE rn = 1
ORDER BY returns DESC;

-- name: q7_day_of_week
-- Q7. Which days of the week are busiest? (staffing question)
SELECT CASE strftime('%w', order_date)
            WHEN '0' THEN 'Sun' WHEN '1' THEN 'Mon' WHEN '2' THEN 'Tue'
            WHEN '3' THEN 'Wed' WHEN '4' THEN 'Thu' WHEN '5' THEN 'Fri' ELSE 'Sat' END AS day,
       strftime('%w', order_date) AS dow_num,
       ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT order_date), 1) AS avg_orders_per_day
FROM orders
GROUP BY dow_num
ORDER BY dow_num;

-- name: q8_customer_value_tiers
-- Q8. How concentrated is revenue? Split customers into 10 equal groups by spend.
WITH spend AS (
    SELECT customer_id,
           SUM(CASE WHEN is_returned = 0 THEN revenue ELSE 0 END) AS net_spend
    FROM v_sales
    GROUP BY customer_id
),
tiers AS (
    SELECT customer_id, net_spend,
           NTILE(10) OVER (ORDER BY net_spend DESC) AS decile
    FROM spend
)
SELECT decile,
       COUNT(*)                     AS customers,
       ROUND(SUM(net_spend), 0)     AS revenue,
       ROUND(100.0 * SUM(SUM(net_spend)) OVER (ORDER BY decile)
             / SUM(SUM(net_spend)) OVER (), 1) AS cumulative_revenue_pct
FROM tiers
GROUP BY decile
ORDER BY decile;

-- name: q9_rfm_base
-- Q9. Recency, Frequency, Monetary value per customer (input for segmentation in Python)
SELECT customer_id,
       CAST(julianday('2025-12-31') - julianday(MAX(order_date)) AS INTEGER) AS recency_days,
       COUNT(DISTINCT order_id)                                             AS frequency,
       ROUND(SUM(CASE WHEN is_returned = 0 THEN revenue ELSE 0 END), 2)     AS monetary
FROM v_sales
GROUP BY customer_id;
