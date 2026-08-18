# Online Retail Analytics — Tableau Public Manual Guide

The ZIP does not include a pre-generated Tableau CSV. First complete the six
pipeline steps in `README.md`, or run the full pipeline once:

```powershell
python run_pipeline.py
```

Only continue with this Tableau guide after the terminal prints
`Pipeline complete` and the final CSV exists.

The Tableau Public workbook contains three dashboards:

1. Executive Overview
2. Customer Segmentation & Value
3. Churn Risk & Retention Priority

## 1. Confirm the single data file

In File Explorer, open:

```text
D:\Project\online-retail-analytics\data\outputs
```

Confirm that this file exists:

```text
tableau_dashboard_dataset.csv
```

This is the only file connected to Tableau. It contains two row types:

| `record_type` | Rows | Used for |
| --- | ---: | --- |
| `Transaction` | 793,609 | Dashboard 1 sales, orders, customers, countries, products, and time filters |
| `Customer` | 5,878 | Dashboards 2–3 RFM segments, risk, clusters, and customer value |

The two grains are stacked, not joined. Transaction rows have customer-analytics
fields blank; customer rows have transaction measures blank. This prevents
customer monetary and predicted value from being repeated for every purchase.

## 2. Connect the only Tableau source

1. Open Tableau Public.
2. From the blank workbook, click `Data` in the top menu.
3. Select `New Data Source`.
4. Under `To a File`, select `Text File`.
5. Open `D:\Project\online-retail-analytics\data\outputs`.
6. Select `tableau_dashboard_dataset.csv`.
7. Click `Open`.
8. Wait for the Data Source preview.
9. Confirm these field types:

| Field | Tableau type |
| --- | --- |
| `record_type` | String |
| `record_id` | String |
| `transaction_id` | Number (whole) |
| `invoice_no` | String |
| `invoice_date` | Date & Time |
| `customer_id` | String |
| `country` | String |
| `description` | String |
| `quantity` | Number (whole) |
| `unit_price` | Number (decimal) |
| `revenue` | Number (decimal) |
| `is_merchandise` | Boolean |
| `monetary` | Number (decimal) |
| `churn_probability` | Number (decimal) |
| `predicted_90d_value` | Number (decimal) |

10. If `invoice_no` or `customer_id` appears as a number, click its type icon and change it to `String`.
11. Click `Sheet 1` at the bottom.
12. Rename the data source to `Online Retail Dashboard Dataset` by right-clicking its name in the Data pane.

Tableau normally displays snake_case fields as readable names. The guide uses the database names so you can identify them exactly.

## 3. Create Dashboard 1 calculated fields

In the Data pane, right-click empty space and select `Create Calculated Field`.

### Average Order Value

```tableau
SUM([revenue]) / COUNTD([invoice_no])
```

Name it `Average Order Value`.

### Total Revenue

```tableau
SUM([revenue])
```

Name it `Total Revenue`.

### Total Orders

```tableau
COUNTD([invoice_no])
```

Name it `Total Orders`.

### Total Customers

```tableau
COUNTD([customer_id])
```

Name it `Total Customers`.

## 4. Dashboard 1 worksheets

All worksheets in all three dashboards use `Online Retail Dashboard Dataset`.

### 4.1 Revenue Trend

1. Rename `Sheet 1` to `Revenue Trend`.
2. Drag `invoice_date` to Columns.
3. Click the pill menu and choose continuous `Month`. The pill must be green and show `MONTH(invoice_date)`.
4. Drag `revenue` to Rows.
5. On Marks, select `Line`.
6. Set Color to `#0F766E`.
7. Increase line Size slightly.
8. To add points, drag a second `revenue` to Rows, choose `Dual Axis`, set the second Marks card to `Circle`, then synchronize the axes and hide the second axis header.
9. Drag `Total Orders`, `Total Customers`, and `Average Order Value` to Tooltip.
10. Format revenue as GBP.
11. Set Fit to `Entire View`.

### 4.2 Top Countries

1. Create a new worksheet named `Top Countries`.
2. Drag `country` to Rows.
3. Drag `revenue` to Columns.
4. Sort descending.
5. Drag `country` to Filters.
6. Open the `Top` tab.
7. Select `By field > Top 10 by SUM(revenue)`.
8. Keep Marks as Bar.
9. Drag `revenue` to Label.
10. Drag `Total Orders`, `Total Customers`, and `Average Order Value` to Tooltip.
11. Use navy or blue; reserve red for churn risk.

### 4.3 Top Products

1. Create `Top Products`.
2. Drag `is_merchandise` to Filters and keep only `True`.
3. Drag `description` to Rows.
4. Drag `revenue` to Columns.
5. Filter `description` to Top 10 by `SUM(revenue)`.
6. Sort descending.
7. Drag `revenue` to Label.
8. Drag `stock_code`, `quantity`, `Total Orders`, and `Total Customers` to Tooltip.
9. Change the aggregation of `quantity` in Tooltip to `SUM`.

The merchandise filter prevents postage, discounts, adjustments, and manual accounting codes from being presented as products.

### 4.4 Orders & AOV

1. Create `Orders & AOV`.
2. Drag `invoice_date` to Columns and choose continuous Month.
3. Drag `invoice_no` to Rows.
4. Open the `invoice_no` pill and change Measure to `Count (Distinct)`.
5. Drag `Average Order Value` to Rows beside the first measure.
6. Right-click the second axis and choose `Dual Axis`.
7. Do not synchronize the axes because order count and GBP have different units.
8. On the `COUNTD(invoice_no)` Marks card, choose Bar and use light blue `#93C5FD`.
9. On the `Average Order Value` Marks card, choose Line and use amber `#F59E0B`.
10. Add circles to the AOV line using the Marks options if desired.

### 4.5 KPI Revenue

1. Create `KPI Revenue`.
2. Drag `Total Revenue` to Text on Marks.
3. Keep Rows and Columns empty.
4. Format as `£#,##0.0,,"M"` or Tableau's equivalent millions format.
5. Set the value to 26–30 pt bold.

### 4.6 KPI Orders

1. Create `KPI Orders`.
2. Drag `Total Orders` to Text.
3. Format as a whole number with thousands separators.

### 4.7 KPI Customers

1. Create `KPI Customers`.
2. Drag `Total Customers` to Text.
3. Format as a whole number with thousands separators.

### 4.8 KPI AOV

1. Create `KPI AOV`.
2. Drag `Average Order Value` to Text.
3. Format as GBP with two decimals.

## 5. Create Country and Year filters correctly

First isolate the correct row grain. This step is mandatory.

### Dashboard 1 record type

1. Open `Revenue Trend`.
2. Drag `record_type` to Filters.
3. Keep only `Transaction`.
4. Click OK.
5. Right-click the `record_type` pill in Filters.
6. Select `Apply to Worksheets > Selected Worksheets`.
7. Select only these eight worksheets:

   - Revenue Trend
   - Top Countries
   - Top Products
   - Orders & AOV
   - KPI Revenue
   - KPI Orders
   - KPI Customers
   - KPI AOV

8. Do not show `record_type` as a user-facing dashboard filter.

Now create Country and Year filters from `Revenue Trend`.

### Country

1. Open `Revenue Trend`.
2. Drag `country` to Filters.
3. Select all values and click OK.
4. Right-click the `country` pill in Filters.
5. Select `Show Filter`.
6. Open the filter-card menu and choose `Multiple Values (Dropdown)`.
7. Open the menu again.
8. Select `Apply to Worksheets > Selected Worksheets`.
9. Select the same eight Dashboard 1 worksheets only.

### Year

1. Drag `transaction_year` to Filters.
2. Select 2009, 2010, and 2011.
3. Click OK.
4. Right-click `transaction_year` in Filters and select `Show Filter`.
5. Set it to `Multiple Values (Dropdown)`.
6. Select `Apply to Worksheets > Selected Worksheets`.
7. Select the same eight Dashboard 1 worksheets only.

Test before assembling the dashboard:

1. Select Country `Germany` and Year `2010`.
2. Open every Dashboard 1 worksheet.
3. Confirm that all KPIs and charts change.
4. If a sheet does not change, check that Country and Year were applied to that selected worksheet.

Coverage warning: 2009 contains only December, and 2011 ends on 9 December. Do not compare those totals as complete calendar years.

## 6. Assemble Dashboard 1

1. Select `Dashboard > New Dashboard`.
2. Rename it `Executive Overview`.
3. Set fixed size to `1440 × 900`.
4. Keep objects Tiled.
5. Add a vertical container covering the canvas.
6. Add a horizontal header container.
7. Put a text title on the left: `Online Retail Executive Overview`.
8. Put the Country and Year filter cards on the right.
9. Add a horizontal KPI container beneath the header.
10. Add `KPI Revenue`, `KPI Orders`, `KPI Customers`, and `KPI AOV`.
11. Add the middle container: Revenue Trend approximately 65%, Top Countries 35%.
12. Add the bottom container: Top Products 50%, Orders & AOV 50%.
13. Add a small note: `December 2011 contains data only through 9 December.`
14. Give cards white backgrounds and 8–12 px padding.
15. Set the canvas background to `#F8FAFC`.

Optional interaction: select the Top Countries sheet inside the dashboard and click `Use as Filter`. Clicking a country bar will then filter the remaining Executive Overview charts.

## 7. Prepare the customer-grain worksheets

Do not add another data source. Every worksheet in Dashboards 2 and 3 uses the
same `tableau_dashboard_dataset.csv` file.

For every Dashboard 2 and Dashboard 3 worksheet:

1. Drag `record_type` to Filters immediately after creating the worksheet.
2. Keep only `Customer`.
3. Click OK.
4. Do not show this technical filter on the dashboard.

After all customer worksheets exist, you may apply the Customer value through
`Apply to Worksheets > Selected Worksheets`, but select only Dashboard 2 and 3
worksheets. Never apply it to Dashboard 1 worksheets.

## 8. Dashboard 2 — Customer Segmentation & Value

### Revenue by RFM Segment

- Rows: `rfm_segment`
- Columns: `SUM(monetary)`
- Color: `rfm_segment`
- Label: `SUM(monetary)`
- Sort descending

### Customer Geography

1. Assign `primary_country` the geographic role Country/Region.
2. Double-click it to generate the map.
3. Set Marks to Circle.
4. Detail: `primary_country`.
5. Size: `COUNTD(customer_id)`.
6. Color: `SUM(monetary)` using one sequential teal palette.
7. Filter out `Unspecified`.
8. Do not assign guessed coordinates to unresolved locations.

### Purchase Frequency vs Customer Value

- Columns: `frequency`
- Rows: `monetary`
- Detail: `customer_id`
- Color: `rfm_segment`
- Size: `monetary`
- Tooltip: country, recency, churn probability, predicted value
- Use logarithmic axes if extreme customers compress the marks

### Customer Mix by Segment

- Rows: `rfm_segment`
- Columns: `COUNTD(customer_id)`
- Color: `rfm_segment`
- Label: distinct customers

### Dashboard 2 layout

```text
Title + Segment filter + Country filter
Customers | Historical Value | Champions | High-Value At Risk
Revenue by RFM Segment (40%) | Customer Geography (60%)
Frequency vs Value (60%)     | Customer Mix (40%)
```

Do not add a recommendation text card. Keep the dashboard analytical.

## 9. Dashboard 3 — Churn Risk & Retention Priority

Create `Retention Priority`:

```tableau
IF [churn_risk_band] = 'High' AND [monetary] >= 5000 THEN '1 — Immediate'
ELSEIF [churn_risk_band] = 'High' THEN '2 — High'
ELSEIF [churn_risk_band] = 'Medium' AND [monetary] >= 1000 THEN '3 — Medium'
ELSE '4 — Monitor'
END
```

This is a transparent portfolio rule, not an inferred treatment recommendation.

### Risk Distribution by RFM Segment

- Rows: `rfm_segment`
- Columns: `COUNTD(customer_id)`
- Color: `churn_risk_band`
- Marks: stacked Bar
- Low green, Medium amber, High red

### Risk–Value Matrix

- Columns: `churn_probability`
- Rows: `monetary`
- Detail: `customer_id`
- Color: `churn_risk_band`
- Size: `predicted_90d_value`
- Add a constant reference line at 0.70
- Use a log monetary axis if required

### Churn Probability Distribution

1. Create bins from `churn_probability` with size 0.05.
2. Columns: probability bin.
3. Rows: `COUNTD(customer_id)`.
4. Color: `churn_risk_band`.

### Priority Customer Ranking

- Rows: `customer_id`
- Columns: `SUM(monetary)`
- Color: `Retention Priority`
- Filter out `4 — Monitor`
- Top 15 by monetary
- Tooltip: country, segment, recency, frequency, probability, value, and `churn_score_method`

The `churn_score_method` tooltip distinguishes model-scored customers from customers assigned the explicit no-recent-purchase rule.

### Dashboard 3 layout

```text
Title + Country / Segment / Risk filters
High-Risk Customers | Revenue at Risk | Avg Probability | Predicted 90-Day Value
Risk by Segment (40%)             | Risk–Value Matrix (60%)
Probability Distribution (38%)    | Priority Customer Ranking (62%)
Thin model footer
```

Footer:

```text
Selected model: Logistic Regression | Test snapshot: 1 Sep 2011
ROC-AUC 0.737 | Precision 0.549 | Recall 0.750
Churn = no order in the following 90 days; decision support, not production deployment.
```

## 10. Style rules

| Role | Color |
| --- | --- |
| Background | `#F8FAFC` |
| Cards | `#FFFFFF` |
| Primary text | `#0F172A` |
| Secondary text | `#64748B` |
| Teal | `#0F766E` |
| Blue | `#3B82F6` |
| Low risk | `#10B981` |
| Medium risk | `#F59E0B` |
| High risk | `#EF4444` |

Use Tableau Book, Arial, or Inter. Avoid 3D charts, rainbow palettes, heavy borders, unnecessary legends, and large explanatory text blocks.

## 11. Publish checks

Before `Publish As`:

- test all filters;
- verify every GBP field uses `£`;
- verify churn probabilities use percentages;
- confirm every worksheet uses the single `Online Retail Dashboard Dataset` source;
- confirm all Dashboard 1 sheets are filtered to `record_type = Transaction`;
- confirm all Dashboard 2–3 sheets are filtered to `record_type = Customer`;
- check that no worksheet shows raw field labels such as `SUM(monetary)`;
- check that December 2011 is marked incomplete;
- confirm no `.env`, database password, or local connection credential is embedded;
- do not describe the published workbook as live or real-time.

Recommended Tableau Public title:

```text
Online Retail Customer Analytics: Segmentation & Churn Risk
```
