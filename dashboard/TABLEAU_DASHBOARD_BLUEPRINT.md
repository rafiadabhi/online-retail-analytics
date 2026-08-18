# Tableau Dashboard Blueprint

Build three dashboards at **1440 × 900 px** using tiled containers. Keep each dashboard to one business question.

## Visual style

Style direction: clean executive analytics with restrained fintech aesthetics.

| Role | Color |
| --- | --- |
| Main background | `#F8FAFC` |
| Card background | `#FFFFFF` |
| Primary navy | `#0F172A` |
| Secondary text | `#64748B` |
| Primary teal | `#0F766E` |
| Positive | `#10B981` |
| Medium risk | `#F59E0B` |
| High risk | `#EF4444` |
| Supporting blue | `#3B82F6` |
| Border/grid line | `#E2E8F0` |

Use Tableau Book, Inter, or Arial. Dashboard title: 24–28 pt semibold. KPI values: 24–30 pt bold. Chart titles: 12–14 pt semibold. Body labels: 9–11 pt.

Formatting rules:

- Use white cards on a light gray canvas.
- Keep only essential gridlines.
- Avoid rainbow palettes and 3D charts.
- Use red only for risk or negative movement.
- Format revenue as `£#,##0.0a` on KPI cards and `£#,##0` in tables.
- Format churn probability as `0.0%`.
- Use no more than six segment colors.
- Add one sentence under each dashboard title explaining the decision it supports.

## Data sources

| Tableau source | Main use |
| --- | --- |
| `retail.tableau_dashboard_dataset` | All three dashboards through explicit row-grain filters |

For Tableau Public, connect only `tableau_dashboard_dataset.csv` from
`data/outputs/`.

Mandatory grain rule:

- every Dashboard 1 worksheet: `record_type = Transaction`;
- every Dashboard 2 and 3 worksheet: `record_type = Customer`.

Apply the technical filter to selected worksheets, never blindly to every
worksheet using the source. Customer rows are one row per customer; transaction
rows are one row per clean line item. Mixing the grains produces invalid totals.

# Dashboard 1 — Executive Overview

Decision question: **How is the retail business performing, and where does revenue come from?**

## Layout

```text
Title + date/country filters
KPI Revenue | KPI Orders | KPI Customers | KPI AOV
Monthly Revenue Trend (two-thirds) | Top Countries (one-third)
Top Products (half) | Monthly Orders & AOV (half)
```

## Worksheets

### 1. KPI — Total Revenue

Source: `tableau_dashboard_dataset`; filter `record_type = Transaction`.

- Marks: Text
- Text: `SUM(revenue)`
- Format: Currency (Custom), display units Millions, one decimal
- Label underneath: `TOTAL REVENUE`

Repeat the same design for:

- `COUNTD(invoice_no)`
- `COUNTD(customer_id)`
- `SUM(revenue) / COUNTD(invoice_no)`

### 2. Monthly Revenue Trend

Source: `tableau_dashboard_dataset`; filter `record_type = Transaction`.

- Columns: `invoice_date` as continuous Month
- Rows: `SUM(revenue)`
- Marks: Line
- Color: `#0F766E`
- Add circles to marks
- Tooltip: month, revenue, orders, active customers, AOV
- Add annotation that December 2011 is incomplete

### 3. Top Countries

Source: `tableau_dashboard_dataset`; filter `record_type = Transaction`.

- Rows: `country`
- Columns: `SUM(revenue)`
- Filter: Top 10 by `SUM(revenue)`
- Sort descending
- Marks: Bar
- Color: navy, with United Kingdom highlighted teal
- Label: revenue

### 4. Top Products

Source: `tableau_dashboard_dataset`; filter `record_type = Transaction`.

- Rows: `description`
- Columns: `SUM(revenue)`
- Filter: Top 10 by revenue
- Filter: `is_merchandise = True`
- Sort descending
- Marks: Bar
- Tooltip: stock code, units, orders, customers, revenue

### 5. Orders and AOV

Source: `tableau_dashboard_dataset`; filter `record_type = Transaction`.

- Columns: `invoice_date` as continuous Month
- Rows: `COUNTD(invoice_no)`
- Add second axis: `SUM(revenue) / COUNTD(invoice_no)`
- Dual axis
- Orders: bar, light blue
- AOV: line, amber
- Do not synchronize axes because units differ

## Dashboard actions

- Show `country` and `YEAR(invoice_date)` as dropdown filters.
- Apply both filters to all worksheets using the executive data source.
- Selecting a country bar can additionally filter all Executive worksheets.
- Selecting a month highlights the same month in supporting charts.
- Include a Reset Filters button.

# Dashboard 2 — Customer Segmentation & Value

Decision question: **Which customer groups create the most value, and where are they geographically concentrated?**

Source: `tableau_dashboard_dataset`; filter every worksheet to
`record_type = Customer`.

## Layout

```text
Title + country/segment filters
KPI Customers | KPI Historical Value | KPI Champions | KPI High-Value At Risk
Segment Revenue Bar (40%) | Customer Geography Map (60%)
Frequency vs Monetary Scatter (60%) | Segment Customer Mix (40%)
```

## Calculated fields

### Customer Count

```tableau
COUNTD([customer_id])
```

### Revenue Share

```tableau
SUM([monetary]) / TOTAL(SUM([monetary]))
```

### High-Value At-Risk Customer

```tableau
IF [rfm_segment] = 'High-Value At Risk' THEN [customer_id] END
```

### Log Monetary

```tableau
LOG([monetary] + 1)
```

### Log Frequency

```tableau
LOG([frequency] + 1)
```

## Worksheets

### 1. Segment Revenue

- Rows: `rfm_segment`
- Columns: `SUM(monetary)`
- Color: `rfm_segment`
- Label: revenue and Revenue Share
- Sort descending by monetary

### 2. Frequency vs Monetary Scatter

- Columns: `Log Frequency`
- Rows: `Log Monetary`
- Detail: `customer_id`
- Color: `rfm_segment`
- Size: `monetary`
- Tooltip: customer, country, recency, frequency, monetary, churn probability
- Add trend line only if it remains readable

### 3. Customer Geography Map

- Geographic field: `primary_country` with Geographic Role = Country/Region
- Marks: Circle map
- Detail: `primary_country`
- Size: `COUNTD(customer_id)`
- Color: `SUM(monetary)` using a single sequential teal palette
- Tooltip: country, customer count, historical revenue, average customer value,
  and average churn probability
- Filters: `primary_country` and `rfm_segment`
- Exclude `Unspecified` and resolve or filter any remaining unknown locations

The map should respond to the RFM segment filter. Its purpose is to show where
each selected segment is concentrated, not to repeat the country ranking from
the Executive Overview.

### 4. Segment Customer Mix

- Rows: `rfm_segment`
- Columns: `COUNTD(customer_id)`
- Color: `rfm_segment`
- Label: customer count and percent of total
- Sort descending by customer count
- Marks: Bar

Do not add a Recommended Actions text card. Recommendations belong in the
project narrative or interview discussion; the dashboard should prioritize
measures, comparisons, and interactive detail.

## Segment colors

| Segment | Color |
| --- | --- |
| Champions | `#0F766E` |
| Loyal Customers | `#3B82F6` |
| New / Potential | `#8B5CF6` |
| Regular Customers | `#94A3B8` |
| High-Value At Risk | `#F59E0B` |
| At Risk | `#EF4444` |

# Dashboard 3 — Churn Risk & Retention Priority

Decision question: **Which high-risk, high-value customers should be reviewed first?**

Source: `tableau_dashboard_dataset`; filter every worksheet to
`record_type = Customer`.

## Layout

```text
Title + country/segment/risk filters
KPI High-Risk Customers | KPI Revenue at Risk | KPI Avg Churn Probability | KPI Predicted 90-Day Value
Risk by Segment (40%) | Risk-Value Matrix (60%)
Churn Probability Distribution (38%) | Priority Customer Ranking (62%)
Thin Model Performance Footer
```

## Calculated fields

### High-Risk Customer Count

```tableau
COUNTD(
    IF [churn_risk_band] = 'High' THEN [customer_id] END
)
```

### Historical Revenue at Risk

```tableau
SUM(
    IF [churn_risk_band] = 'High' THEN [monetary] END
)
```

### Predicted 90-Day Value

```tableau
SUM([predicted_90d_value])
```

### Retention Priority

```tableau
IF [churn_risk_band] = 'High' AND [monetary] >= 5000 THEN '1 — Immediate'
ELSEIF [churn_risk_band] = 'High' THEN '2 — High'
ELSEIF [churn_risk_band] = 'Medium' AND [monetary] >= 1000 THEN '3 — Medium'
ELSE '4 — Monitor'
END
```

## Worksheets

### 1. Risk by Segment

- Rows: `rfm_segment`
- Columns: `COUNTD(customer_id)`
- Color: `churn_risk_band`
- Marks: Bar
- Analysis: Stack Marks On
- Risk colors: Low green, Medium amber, High red

### 2. Risk-Value Matrix

- Columns: `churn_probability`
- Rows: `monetary`; use a logarithmic axis if the outliers compress the view
- Detail: `customer_id`
- Color: `churn_risk_band`
- Size: `predicted_90d_value`
- Tooltip: customer, country, RFM segment, recency, frequency, monetary,
  churn probability, predicted 90-day value, churn score method, and Retention Priority
- Add a vertical reference line at churn probability `0.70`
- Add a horizontal median reference line for `monetary`

The upper-right region contains the most valuable customers with the highest
modelled inactivity risk. This is a prioritization view, not a causal treatment
recommendation.

### 3. Churn Probability Distribution

- Create bins from `churn_probability`, bin size 0.05
- Columns: probability bin
- Rows: `COUNTD(customer_id)`
- Color: `churn_risk_band`
- Marks: Bar
- Add a reference line at 0.70

### 4. Priority Customer Ranking

- Rows: `customer_id`
- Columns: `SUM(monetary)`
- Color: `Retention Priority`
- Label: historical value
- Filter: exclude `Retention Priority = 4 — Monitor`
- Filter: Top 15 customers by `SUM(monetary)` after the priority filter
- Sort by Retention Priority, then monetary descending
- Tooltip: country, RFM segment, recency, frequency, churn probability,
  predicted 90-day value, and churn score method
- Use red only for Immediate, amber for High, blue for Medium

Do not include a Suggested Action column. The ranking should communicate who
needs review first; the intervention itself requires business policy and cannot
be inferred from this historical dataset.

### 5. Model Performance Footer

Display a small text note:

```text
Best model: Logistic Regression
Out-of-time test ROC-AUC: 0.737 | Recall: 0.750 | Test snapshot: 1 Sep 2011
Churn definition: no order in the following 90 days
```

Do not present the score as production-grade certainty.

# Dashboard assembly order

1. Create every worksheet first.
2. Create a 1440 × 900 dashboard.
3. Add a vertical tiled container.
4. Add the title/filter horizontal container.
5. Add KPI cards in one horizontal container.
6. Add chart containers.
7. Set inner padding to 8–12 px.
8. Set outer padding to 20–24 px.
9. Apply fonts and colors consistently.
10. Test every filter and dashboard action.
11. Hide unused sheet titles and legends.
12. Publish only after checking tooltips and number formats.

# Style references

Use these as layout inspiration, not as designs to copy blindly:

- Tableau Dashboard Showcase: https://www.tableau.com/data-insights/dashboard-showcase
- Customer Segmentation & Transaction Analytics: https://public.tableau.com/app/profile/shwetasavale/viz/CustomerSegmentationTransactionAnalyticsDashboard/CustomerSegmentationTransactionAnalyticsDashboard
- RFM Analysis — Customer Segmentation: https://public.tableau.com/app/profile/.83057946/viz/RFMAnalysis-CustomerSegmentation/Segmentation
- E-Commerce Churn Analysis: https://public.tableau.com/app/profile/ariq.fauzan/viz/E-CommerceChurnAnalysisDashboard/Dashboard1-Overview

Prefer the clean spacing and information hierarchy of these examples. Do not copy their datasets, claims, or colors without adapting them to this project.
