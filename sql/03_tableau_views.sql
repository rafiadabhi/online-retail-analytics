DROP VIEW IF EXISTS retail.tableau_dashboard_dataset;
DROP VIEW IF EXISTS retail.tableau_kpi;
DROP VIEW IF EXISTS retail.tableau_customer_dashboard;
DROP VIEW IF EXISTS retail.tableau_monthly_sales;
DROP VIEW IF EXISTS retail.tableau_country_performance;
DROP VIEW IF EXISTS retail.tableau_product_performance;
DROP VIEW IF EXISTS retail.tableau_executive_dashboard;

CREATE VIEW retail.tableau_executive_dashboard AS
SELECT
    transaction_id,
    invoice_no,
    stock_code,
    COALESCE(description, 'Unknown Product') AS description,
    quantity,
    invoice_date,
    unit_price,
    customer_id,
    country,
    source_period,
    revenue,
    stock_code ~ '^[0-9]{5}[A-Z]?$' AS is_merchandise
FROM retail.transactions;

CREATE VIEW retail.tableau_customer_dashboard AS
SELECT
    f.customer_id,
    f.primary_country,
    f.first_purchase_date,
    f.last_purchase_date,
    f.recency_days,
    f.frequency,
    f.monetary,
    f.average_order_value,
    f.total_items,
    f.unique_products,
    f.active_months,
    f.tenure_days,
    f.avg_days_between_orders,
    f.rfm_score,
    f.rfm_segment,
    f.rule_based_churn_status,
    a.rfm_cluster,
    a.churn_probability,
    a.churn_risk_band,
    a.predicted_90d_value,
    a.churn_score_method
FROM retail.customer_features f
LEFT JOIN retail.customer_analytics a USING (customer_id);

CREATE VIEW retail.tableau_dashboard_dataset AS
SELECT
    'Transaction'::text AS record_type,
    'T-' || e.transaction_id::text AS record_id,
    e.transaction_id,
    e.invoice_no,
    e.invoice_date,
    EXTRACT(YEAR FROM e.invoice_date)::integer AS transaction_year,
    DATE_TRUNC('month', e.invoice_date)::date AS transaction_month,
    e.source_period,
    e.stock_code,
    e.description,
    e.quantity,
    e.unit_price,
    e.customer_id,
    e.country,
    e.revenue,
    e.is_merchandise,
    NULL::text AS primary_country,
    NULL::date AS first_purchase_date,
    NULL::date AS last_purchase_date,
    NULL::integer AS recency_days,
    NULL::bigint AS frequency,
    NULL::numeric(14, 2) AS monetary,
    NULL::numeric(14, 2) AS average_order_value,
    NULL::bigint AS total_items,
    NULL::bigint AS unique_products,
    NULL::bigint AS active_months,
    NULL::integer AS tenure_days,
    NULL::numeric(10, 2) AS avg_days_between_orders,
    NULL::integer AS rfm_score,
    NULL::text AS rfm_segment,
    NULL::text AS rule_based_churn_status,
    NULL::integer AS rfm_cluster,
    NULL::numeric(6, 4) AS churn_probability,
    NULL::text AS churn_risk_band,
    NULL::numeric(16, 2) AS predicted_90d_value,
    NULL::text AS churn_score_method
FROM retail.tableau_executive_dashboard e

UNION ALL

SELECT
    'Customer'::text AS record_type,
    'C-' || c.customer_id AS record_id,
    NULL::bigint AS transaction_id,
    NULL::text AS invoice_no,
    NULL::timestamp AS invoice_date,
    NULL::integer AS transaction_year,
    NULL::date AS transaction_month,
    NULL::text AS source_period,
    NULL::text AS stock_code,
    NULL::text AS description,
    NULL::integer AS quantity,
    NULL::numeric(12, 3) AS unit_price,
    c.customer_id,
    c.primary_country AS country,
    NULL::numeric(14, 3) AS revenue,
    NULL::boolean AS is_merchandise,
    c.primary_country,
    c.first_purchase_date,
    c.last_purchase_date,
    c.recency_days,
    c.frequency,
    c.monetary,
    c.average_order_value,
    c.total_items,
    c.unique_products,
    c.active_months,
    c.tenure_days,
    c.avg_days_between_orders,
    c.rfm_score,
    c.rfm_segment,
    c.rule_based_churn_status,
    c.rfm_cluster,
    c.churn_probability,
    c.churn_risk_band,
    c.predicted_90d_value,
    c.churn_score_method
FROM retail.tableau_customer_dashboard c;
