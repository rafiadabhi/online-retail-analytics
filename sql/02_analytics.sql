DROP MATERIALIZED VIEW IF EXISTS retail.customer_order_history CASCADE;
DROP MATERIALIZED VIEW IF EXISTS retail.monthly_sales CASCADE;
DROP MATERIALIZED VIEW IF EXISTS retail.country_performance CASCADE;
DROP MATERIALIZED VIEW IF EXISTS retail.product_performance CASCADE;
DROP TABLE IF EXISTS retail.customer_features CASCADE;

CREATE MATERIALIZED VIEW retail.customer_order_history AS
WITH invoice_level AS (
    SELECT
        customer_id,
        invoice_no,
        MIN(invoice_date) AS order_timestamp,
        MIN(invoice_date)::date AS order_date,
        SUM(revenue)::numeric(14, 2) AS order_revenue,
        SUM(quantity)::bigint AS items_purchased,
        COUNT(DISTINCT stock_code) AS unique_products,
        MODE() WITHIN GROUP (ORDER BY country) AS country
    FROM retail.transactions
    GROUP BY customer_id, invoice_no
)
SELECT
    customer_id,
    invoice_no,
    order_timestamp,
    order_date,
    order_revenue,
    items_purchased,
    unique_products,
    country,
    LAG(order_date) OVER (
        PARTITION BY customer_id
        ORDER BY order_timestamp, invoice_no
    ) AS previous_order_date,
    order_date - LAG(order_date) OVER (
        PARTITION BY customer_id
        ORDER BY order_timestamp, invoice_no
    ) AS days_since_previous_order
FROM invoice_level;

CREATE INDEX idx_order_history_customer
    ON retail.customer_order_history (customer_id);
CREATE INDEX idx_order_history_date
    ON retail.customer_order_history (order_date);

CREATE TABLE retail.customer_features AS
WITH analysis_date AS (
    SELECT MAX(invoice_date)::date AS date
    FROM retail.transactions
),
product_features AS (
    SELECT
        customer_id,
        COUNT(DISTINCT stock_code) AS lifetime_unique_products,
        COUNT(DISTINCT DATE_TRUNC('month', invoice_date)) AS active_months
    FROM retail.transactions
    GROUP BY customer_id
),
customer_aggregates AS (
    SELECT
        h.customer_id,
        MIN(h.order_date) AS first_purchase_date,
        MAX(h.order_date) AS last_purchase_date,
        COUNT(DISTINCT h.invoice_no) AS frequency,
        SUM(h.order_revenue)::numeric(14, 2) AS monetary,
        AVG(h.order_revenue)::numeric(14, 2) AS average_order_value,
        SUM(h.items_purchased)::bigint AS total_items,
        AVG(h.days_since_previous_order)::numeric(10, 2) AS avg_days_between_orders,
        MODE() WITHIN GROUP (ORDER BY h.country) AS primary_country
    FROM retail.customer_order_history h
    GROUP BY h.customer_id
),
rfm AS (
    SELECT
        c.*,
        p.lifetime_unique_products AS unique_products,
        p.active_months,
        a.date - c.last_purchase_date AS recency_days,
        c.last_purchase_date - c.first_purchase_date AS tenure_days
    FROM customer_aggregates c
    CROSS JOIN analysis_date a
    JOIN product_features p USING (customer_id)
),
scored AS (
    SELECT
        rfm.*,
        NTILE(4) OVER (ORDER BY recency_days DESC) AS recency_score,
        NTILE(4) OVER (ORDER BY frequency ASC) AS frequency_score,
        NTILE(4) OVER (ORDER BY monetary ASC) AS monetary_score
    FROM rfm
)
SELECT
    scored.*,
    recency_score + frequency_score + monetary_score AS rfm_score,
    CASE
        WHEN recency_score = 4 AND frequency_score >= 3 AND monetary_score >= 3
            THEN 'Champions'
        WHEN recency_score >= 3 AND frequency_score >= 3
            THEN 'Loyal Customers'
        WHEN recency_score = 4 AND frequency_score <= 2
            THEN 'New / Potential'
        WHEN recency_score <= 2 AND monetary_score >= 3
            THEN 'High-Value At Risk'
        WHEN recency_score = 1
            THEN 'At Risk'
        ELSE 'Regular Customers'
    END AS rfm_segment,
    CASE
        WHEN recency_days > 90 THEN 'High Risk'
        WHEN recency_days > 60 THEN 'Watchlist'
        ELSE 'Active'
    END AS rule_based_churn_status
FROM scored;

ALTER TABLE retail.customer_features
    ADD PRIMARY KEY (customer_id);

CREATE MATERIALIZED VIEW retail.monthly_sales AS
SELECT
    DATE_TRUNC('month', invoice_date)::date AS month,
    COUNT(DISTINCT invoice_no) AS total_orders,
    COUNT(DISTINCT customer_id) AS active_customers,
    SUM(quantity)::bigint AS items_sold,
    SUM(revenue)::numeric(16, 2) AS revenue,
    (SUM(revenue) / NULLIF(COUNT(DISTINCT invoice_no), 0))::numeric(14, 2)
        AS average_order_value
FROM retail.transactions
GROUP BY DATE_TRUNC('month', invoice_date)::date;

CREATE UNIQUE INDEX idx_monthly_sales_month
    ON retail.monthly_sales (month);

CREATE MATERIALIZED VIEW retail.country_performance AS
SELECT
    country,
    COUNT(DISTINCT customer_id) AS customers,
    COUNT(DISTINCT invoice_no) AS orders,
    SUM(revenue)::numeric(16, 2) AS revenue,
    (SUM(revenue) / NULLIF(COUNT(DISTINCT invoice_no), 0))::numeric(14, 2)
        AS average_order_value
FROM retail.transactions
GROUP BY country;

CREATE UNIQUE INDEX idx_country_performance_country
    ON retail.country_performance (country);

CREATE MATERIALIZED VIEW retail.product_performance AS
SELECT
    stock_code,
    COALESCE(MAX(description), 'Unknown Product') AS description,
    SUM(quantity)::bigint AS units_sold,
    COUNT(DISTINCT invoice_no) AS orders,
    COUNT(DISTINCT customer_id) AS customers,
    SUM(revenue)::numeric(16, 2) AS revenue
FROM retail.transactions
WHERE stock_code ~ '^[0-9]{5}[A-Z]?$'
GROUP BY stock_code;

CREATE UNIQUE INDEX idx_product_performance_stock_code
    ON retail.product_performance (stock_code);
