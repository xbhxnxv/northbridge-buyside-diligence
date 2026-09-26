# Power BI dashboard: build plan

This folder has everything needed to build the Northbridge dashboard in Power BI Desktop and to check it against the analysis. The `.pbix` itself has to be built by hand; the steps are at the end.

| File | What it is |
|---|---|
| `model_data/*.csv` | Star-schema tables exported by `export_model_data.py` (rebuilt by `python run_all.py`) |
| `measures.dax` | Every measure, with comments |
| `expected_values.csv` | Each measure computed in Python for a set of filter contexts, to check the Power BI numbers |
| `screenshots/` | Put one PNG per page here once built |

## 1. Model

| Table | Grain | Key | Rows |
|---|---|---|---|
| `FactRevenue` | customer × product × month | customer_id, product_id, month_start | one per cell with any billing or credit |
| `FactMRR` | customer × product × month | customer_id, product_id, month_start | recurring billings before credit notes, non-zero only |
| `FactCost` | product line × month | product_line, month_start | 192 |
| `DimCustomer` | customer | customer_id | cohort, size band, region, region group, channel, industry, flags |
| `DimProduct` | product | product_id | product line, revenue type, list price |
| `DimProductLine` | product line | product_line | line type, sort order |
| `DimDate` | month | month_start | year, quarter, month number, year-end flag |

## 2. Relationships

All are one-to-many, single direction, filtering from the dimension to the fact.

| From (one) | To (many) | Key |
|---|---|---|
| `DimDate[month_start]` | `FactRevenue[month_start]` | month |
| `DimDate[month_start]` | `FactMRR[month_start]` | month |
| `DimDate[month_start]` | `FactCost[month_start]` | month |
| `DimCustomer[customer_id]` | `FactRevenue[customer_id]` | customer |
| `DimCustomer[customer_id]` | `FactMRR[customer_id]` | customer |
| `DimProduct[product_id]` | `FactRevenue[product_id]` | product |
| `DimProduct[product_id]` | `FactMRR[product_id]` | product |
| `DimProductLine[product_line]` | `DimProduct[product_line]` | product line |
| `DimProductLine[product_line]` | `FactCost[product_line]` | product line |

**Why FactCost joins through a product-line dimension.** Costs exist only at product line × month; there is no product or customer grain. Joining `FactCost` directly to `DimProduct` would be many-to-many (three Core Platform tiers share one cost line). A separate `DimProductLine` table sits above `DimProduct` (a one-level snowflake) and filters both `DimProduct`, and through it the revenue facts, and `FactCost`. One product-line slicer built on `DimProductLine[product_line]` then filters revenue, MRR and cost consistently. Customer attributes cannot filter `FactCost`, which is why the gross profit measures return blank under a customer filter.

Mark `DimDate` as the date table on `month_start`. Sort `DimCustomer[size_band]` by `size_band_order` and `DimProductLine[product_line]` by `line_order`.

## 3. Measures

See `measures.dax`. The ones on the pages:

| Measure | Definition in short |
|---|---|
| Net Revenue, Recurring Revenue, One-off Revenue, Other Implementation Revenue | Sums of the cube columns |
| Recurring % | Recurring / net |
| MRR | MRR at the last month in context |
| ARR | December MRR × 12 for the year in context |
| Active Customers | Customers with MRR in the last month in context |
| NRR, GRR | December Y MRR of December Y−1 customers / their December Y−1 MRR; GRR capped per customer. **2023 to 2025 only** |
| Logo Churn Rate | December Y−1 customers with no MRR in December Y |
| Top 10 Concentration % | TOPN over customers on net revenue; ignores customer slicers |
| Gross Profit, Gross Margin % | Net revenue less cost of delivery; blank under customer filters |
| YoY versions | Net Revenue YoY %, Recurring Revenue YoY %, ARR YoY %, Gross Margin Change (pts) |

## 4. Pages

Every page has the same slicer bar at the top and a source note at the bottom: "Source: Northbridge data room (synthetic), cleaned invoice ledger. Definitions: docs/metric_definitions.md."

**Page 1: Executive summary**
```
+------------------------------------------------------------------------------------+
| Year | Product line | Region | Size band                          (synced slicers) |
+------------+------------+------------+------------+------------+-----------+-------+
| Net        | ARR        | Recurring  | NRR        | GRR        | Top 10    | Gross |
| Revenue    | (Dec x 12) | %          | (23-25)    | (23-25)    | share     | margin|
| + YoY %    | + YoY %    |            |            |            |           | %     |
+------------+------------+------------+------------+------------+-----------+-------+
| Net revenue by year, stacked:           | ARR by year-end (column) with         |
| recurring / signup impl. / other impl.  | ARR YoY % as data labels              |
+-----------------------------------------+----------------------------------------+
| Text box: three headline findings (from outputs/key_findings.md)                   |
+------------------------------------------------------------------------------------+
```

**Page 2: Revenue quality**
- Clustered column: Net Revenue YoY % against Recurring Revenue YoY % by year.
- Stacked column: net revenue by product line by year.
- Table: year, recurring, one-off, other implementation, recurring %.
- Card: Other Implementation Revenue (2025).

**Page 3: Customers and retention**
- Line: Active Customers by month.
- Clustered column: NRR and GRR by year (2023 to 2025; note the limit in the title).
- Column: Logo Churn Rate by year.
- Matrix heatmap: `DimCustomer[cohort]` on rows, `Tenure[Value]` on columns, `Cohort Active Customers` divided by cohort size (conditional formatting, blue scale). Cohort visuals ignore the year slicer.
- Bar: Logo Churn Rate by channel (2025), sorted descending.
- Card: Top 10 Concentration %.

**Page 4: ARR bridge**
- Waterfall visual: category = component, values from a small bridge table. Load `outputs/tables/4e_arr_bridge_long.csv` as a separate table `ARRBridge` (year, component, arr, order) not related to the model, add a year slicer bound to `ARRBridge[year]` (not synced), sort component by order.
- Table beside it: component and £ for the selected year; a check row showing opening + components = closing.

**Page 5: Margins**
- Line: Gross Margin % by year, one line per product line (legend `DimProductLine[product_line]`).
- Column: Gross Profit by year.
- Card: Gross Margin Change (pts).
- Text: "Gross margin is not available by region or size band: costs exist only by product line."

## 5. Slicers

Year (`DimDate[year]`), product line (`DimProductLine[product_line]`), region group (`DimCustomer[region_group]`) and size band (`DimCustomer[size_band]`), synced across pages 1, 2, 3 and 5 (View > Sync slicers).

Measures that deliberately ignore a slicer:

| Measure | Ignores | How |
|---|---|---|
| Top 10 Concentration % | region, size band, any customer filter | `REMOVEFILTERS ( DimCustomer )` inside the measure |
| Cohort Active Customers, Cohort Revenue Retention | year | `REMOVEFILTERS ( DimDate )` for each tenure month |
| NRR, GRR, Logo Churn Rate, ARR | months within the year | they read December of the year in context, not the months selected |
| Gross Profit, Gross Margin % | returns blank under customer filters | `IF ( NOT ISCROSSFILTERED ( DimCustomer ), ... )` |

To exclude a visual from a slicer entirely, use Format > Edit interactions and set the slicer to "None" for that visual (used for the ARR bridge page, which has its own year slicer).

## 6. Checking the build

`expected_values.csv` has one row per measure and filter context:

| Column | Meaning |
|---|---|
| context | `year`, `year x product line`, `2025 x region_group`, `2025 x region`, `2025 x size_band` |
| year | calendar year set on the year slicer |
| filter_column, filter_value | the other slicer (blank for year only) |
| measure | measure name in `measures.dax` |
| value | expected value; ratios as fractions (0.9544 = 95.44%); blank where the measure is blank |

Build a table visual with the measures, set the slicers to a context, and compare. The year rows are tested against the Step 4 outputs (`tests/test_tieouts.py::test_expected_values_agree_with_step4`). TOPN returns more than ten customers when two tie on revenue at the boundary; none do in this data.

## 7. Build steps

1. Open Power BI Desktop. Get data > Text/CSV, load all seven files in `dashboard/model_data/`. In Power Query set types: `month_start` and `signup_date` as Date, ids as Text, money columns as Fixed decimal number, flags as True/False. Close and apply.
2. Model view: delete any relationships Power BI created automatically, then create the nine relationships in section 2 (one-to-many, single direction).
3. Mark `DimDate` as the date table (`month_start`). Set sort-by columns: `size_band` by `size_band_order`, `product_line` by `line_order`, `month_name` by `month_number`.
4. Hide the key columns in the fact tables and the sort-order columns.
5. Enter data to create an empty table `_Measures`. Add each measure from `measures.dax` (New measure, paste the expression). Format: £ measures as currency with no decimals in thousands (display units: thousands), percentages as percentage with one decimal.
6. Create the calculated table `Tenure = GENERATESERIES ( 0, 48, 1 )`.
7. Load `outputs/tables/4e_arr_bridge_long.csv` as `ARRBridge` (no relationships).
8. Build the five pages in section 4. Add the four slicers to page 1, then View > Sync slicers to sync them to pages 2, 3 and 5.
9. Check the numbers against `expected_values.csv` for at least: each year; 2025 × Core Platform; 2025 × EU; 2025 × Large (250+).
10. Export one screenshot per page (File > Export > PDF, or a screen capture) to `dashboard/screenshots/` as `01_executive_summary.png` to `05_margins.png`.
