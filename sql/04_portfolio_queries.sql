-- Run this file in pgAdmin 4 > online_retail_db > Query Tool.
-- Each section can also be executed separately.

-- 1. Data validation after loading
SELECT
    COUNT(*) AS transaction_rows,
    COUNT(DISTINCT invoice_no) AS orders,
    COUNT(DISTINCT customer_id) AS customers,
    MIN(invoice_date) AS first_transaction,
    MAX(invoice_date) AS last_transaction,
    SUM(revenue) AS total_revenue
FROM retail.transactions;

-- 2. Monthly sales trend and month-over-month growth
WITH monthly AS (
    SELECT
        DATE_TRUNC('month', invoice_date)::date AS month,
        SUM(revenue) AS revenue
    FROM retail.transactions
    GROUP BY 1
),
growth AS (
    SELECT
        month,
        revenue,
        LAG(revenue) OVER (ORDER BY month) AS previous_month_revenue
    FROM monthly
)
SELECT
    month,
    revenue,
    previous_month_revenue,
    ROUND(
        100.0 * (revenue - previous_month_revenue)
        / NULLIF(previous_month_revenue, 0),
        2
    ) AS month_over_month_growth_pct
FROM growth
ORDER BY month;

-- 3. Country performance
SELECT
    country,
    customers,
    orders,
    revenue,
    average_order_value
FROM retail.country_performance
ORDER BY revenue DESC;

-- 4. Top merchandise products
SELECT
    stock_code,
    description,
    units_sold,
    orders,
    customers,
    revenue
FROM retail.product_performance
ORDER BY revenue DESC
LIMIT 20;

-- 5. RFM segment size and revenue contribution
SELECT
    rfm_segment,
    COUNT(*) AS customers,
    SUM(monetary) AS historical_revenue,
    ROUND(AVG(recency_days), 1) AS average_recency,
    ROUND(AVG(frequency), 1) AS average_frequency,
    ROUND(AVG(monetary), 2) AS average_monetary
FROM retail.customer_features
GROUP BY rfm_segment
ORDER BY historical_revenue DESC;

-- 6. Machine-learning churn risk distribution
SELECT
    churn_risk_band,
    COUNT(*) AS customers,
    ROUND(AVG(churn_probability)::numeric, 4) AS average_probability,
    SUM(f.monetary) AS historical_revenue,
    SUM(a.predicted_90d_value) AS predicted_90d_value
FROM retail.customer_analytics a
JOIN retail.customer_features f USING (customer_id)
GROUP BY churn_risk_band
ORDER BY CASE churn_risk_band
    WHEN 'High' THEN 1
    WHEN 'Medium' THEN 2
    ELSE 3
END;

-- 7. High-value customers requiring retention action
SELECT
    f.customer_id,
    f.primary_country,
    f.rfm_segment,
    f.recency_days,
    f.frequency,
    f.monetary,
    a.churn_probability,
    a.predicted_90d_value
FROM retail.customer_features f
JOIN retail.customer_analytics a USING (customer_id)
WHERE a.churn_risk_band = 'High'
ORDER BY f.monetary DESC
LIMIT 50;

-- 8. Model evaluation metrics
SELECT
    model_type,
    model_name,
    evaluation_split,
    evaluation_snapshot,
    metric,
    ROUND(value::numeric, 4) AS value,
    selected_model
FROM retail.model_metrics
ORDER BY model_type, evaluation_split, model_name, metric;

-- 9. Customer order gaps using the LAG window function
SELECT
    customer_id,
    invoice_no,
    order_date,
    previous_order_date,
    days_since_previous_order,
    order_revenue
FROM retail.customer_order_history
WHERE previous_order_date IS NOT NULL
ORDER BY customer_id, order_date
LIMIT 100;

-- 10. Pareto contribution: cumulative customer revenue share
WITH ranked_customers AS (
    SELECT
        customer_id,
        monetary,
        SUM(monetary) OVER (ORDER BY monetary DESC) AS cumulative_revenue,
        SUM(monetary) OVER () AS total_revenue,
        ROW_NUMBER() OVER (ORDER BY monetary DESC) AS customer_rank,
        COUNT(*) OVER () AS total_customers
    FROM retail.customer_features
)
SELECT
    customer_rank,
    customer_id,
    monetary,
    ROUND(100.0 * customer_rank / total_customers, 2) AS customer_pct,
    ROUND(100.0 * cumulative_revenue / total_revenue, 2) AS cumulative_revenue_pct
FROM ranked_customers
ORDER BY customer_rank;
