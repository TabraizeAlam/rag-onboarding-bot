# Data Pipeline Workflow — Build, Test, Deploy

This document describes how a data pipeline goes from an idea to production on the AIMCo Data Platform.

## Overview: Medallion Architecture

The data platform uses a **three-layer Medallion architecture** implemented in Snowflake:

```
External Sources
      ↓
  [Bronze Layer]  RAW_DB.*
  Raw, unmodified data. Loaded by ingestion jobs.
  No business logic. No joins. Kept indefinitely.
      ↓
  [Silver Layer]  INTERMEDIATE_DB.*
  Cleaned, deduplicated, type-cast, joined data.
  Built by dbt staging and intermediate models.
  Business logic starts here.
      ↓
  [Gold Layer]  ANALYTICS_DB.*
  Business-ready data marts and aggregates.
  Consumed by Power BI, analysts, downstream APIs.
  Named for business concepts (e.g. `fct_portfolio_returns`).
```

---

## Data Sources

Common source categories (all listed publicly in AIMCo's investor communications):

| Source Type | Examples |
|------------|---------|
| Market data vendors | Bloomberg, FactSet (market prices, benchmarks) |
| Portfolio management system | Internal investment book of record (IBOR) |
| Risk systems | VaR and attribution data feeds |
| Corporate reference data | Security master, counterparty data |
| Finance/ERP | GL extracts, expense allocations |
| HR systems | Headcount and org structure feeds |

Each source is ingested into the Bronze layer via an ingestion job — either a Databricks notebook (for files/APIs) or Snowflake's COPY INTO command (for stage-loaded files).

---

## Step-by-Step Pipeline Development

### 1. Define the business requirement

Before writing any code:
- Create a ticket in Azure DevOps Boards with: the data consumer, the output format, the source data, and the SLA.
- Check Atlan to see if a similar model already exists.
- Get sign-off from the requestor on the column definitions before building.

### 2. Build the Bronze ingestion job

If the source does not already land in `RAW_DB`, create an ingestion job:

**For file-based sources (common for vendor feeds):**
```python
# Databricks notebook — load CSV from Azure Blob Storage to Snowflake Bronze
from pyspark.sql import SparkSession

spark = SparkSession.builder.getOrCreate()
df = spark.read.csv("abfss://raw@aimcostorage.dfs.core.windows.net/bloomberg/prices/", header=True)
df.write.format("snowflake") \
    .options(**snowflake_options) \
    .option("dbtable", "RAW_DB.BLOOMBERG.PRICES_RAW") \
    .mode("append") \
    .save()
```

**For API-based sources:**
Use the existing `ingestion_framework` Python package in the `DataPlatform` repo. It handles retry logic, logging, and error alerting automatically.

### 3. Build dbt Silver models

Silver models live in `models/staging/` and `models/intermediate/`:

```sql
-- models/staging/bloomberg/stg_bloomberg__prices.sql
with source as (
    select * from {{ source('bloomberg', 'prices_raw') }}
),

renamed as (
    select
        security_id::varchar       as security_id,
        price_date::date           as price_date,
        close_price::numeric(18,6) as close_price,
        currency_code::varchar(3)  as currency_code,
        loaded_at::timestamp_ntz   as loaded_at
    from source
    where security_id is not null
      and price_date is not null
)

select * from renamed
```

Naming convention: `stg_<source>__<entity>.sql` (double underscore separates source from entity).

### 4. Build dbt Gold models

Gold models live in `models/marts/<domain>/`:

```sql
-- models/marts/investments/fct_portfolio_returns.sql
with returns as (
    select
        portfolio_id,
        return_date,
        gross_return,
        benchmark_return,
        gross_return - benchmark_return as active_return
    from {{ ref('int_portfolio__calculated_returns') }}
)

select * from returns
```

All Gold models must have:
- A `.yml` file with column descriptions
- At least `not_null` and `unique` dbt tests on primary keys
- An Atlan asset entry (auto-synced via the dbt-Atlan integration — just run `dbt docs generate`)

### 5. Add Soda data quality checks

Every Silver and Gold model needs a Soda check file in `checks/<layer>/<model>.yml`:

```yaml
# checks/marts/investments/fct_portfolio_returns.yml
checks for fct_portfolio_returns:
  - missing_count(portfolio_id) = 0
  - missing_count(return_date) = 0
  - duplicate_count(portfolio_id, return_date) = 0
  - min(gross_return) >= -1.0:
      name: No return below -100%
  - row_count > 0
```

Soda checks run automatically in CI after dbt tests pass.

### 6. Open a pull request

```bash
git checkout -b feature/TICKET-123-bloomberg-prices-pipeline
git add .
git commit -m "feat: add Bloomberg daily prices ingestion and Silver model"
git push origin feature/TICKET-123-bloomberg-prices-pipeline
```

Open a PR in Azure DevOps Repos. Required before merging:
- CI pipeline passes (dbt compile + dbt test + Soda checks)
- At least one Senior Data Developer approval
- No unresolved comments

### 7. Deploy to production

Merging to `main` triggers the CD pipeline:
1. `dbt run --select <changed_models>+` on the production Snowflake warehouse
2. `dbt test --select <changed_models>+`
3. Soda scan runs on affected models
4. Databricks workflow triggered if ingestion job changed

If any step fails, the pipeline stops and an alert fires to #data-platform-alerts in Teams.

---

## Orchestration

Production pipelines run on a schedule managed in **Databricks Workflows**:

| Schedule | What runs |
|----------|----------|
| Daily 2:00 AM MT | All Bronze ingestion jobs |
| Daily 4:00 AM MT | Silver dbt models (full refresh weekly, incremental daily) |
| Daily 6:00 AM MT | Gold dbt models + Soda checks |
| Daily 7:00 AM MT | Power BI dataset refresh triggered |

Failed runs page the on-call data engineer via PagerDuty.

---

## Incremental vs Full Refresh Models

Use `incremental` materialization for large fact tables (>1M rows):

```sql
{{ config(materialized='incremental', unique_key='portfolio_id || return_date') }}

select * from {{ ref('int_portfolio__calculated_returns') }}
{% if is_incremental() %}
  where return_date > (select max(return_date) from {{ this }})
{% endif %}
```

Use `table` materialization for dimension tables and anything < 500K rows where simplicity matters more than speed.
