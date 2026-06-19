# Data Platform Architecture

This document describes the end-to-end architecture of AIMCo's Enterprise Data Platform. It is intended to help new team members understand how the pieces fit together before diving into individual components.

---

## Architecture Overview

```
External Data Sources
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│              INGESTION LAYER (Azure + Databricks)               │
│  • Databricks notebooks (PySpark) for file-based vendor feeds   │
│  • Snowpipe for continuous/streaming ingestion                  │
│  • Python ingestion_framework for REST API sources              │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│              BRONZE LAYER (RAW_DB in Snowflake)                 │
│  Raw, unmodified copies of source data                          │
│  • Append-only; never updated or deleted in-place               │
│  • Timestamped with `loaded_at` for full audit trail            │
│  • Partitioned by source and load date                          │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼  (dbt staging models)
┌─────────────────────────────────────────────────────────────────┐
│              SILVER LAYER (INTERMEDIATE_DB in Snowflake)        │
│  Cleaned, typed, deduplicated, and lightly joined data          │
│  • stg_* models: one-to-one with Bronze sources, cleaned only   │
│  • int_* models: cross-source joins and business calculations   │
│  • Full dbt test coverage                                       │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼  (dbt mart models)
┌─────────────────────────────────────────────────────────────────┐
│              GOLD LAYER (ANALYTICS_DB in Snowflake)             │
│  Business-ready data marts — named for business concepts        │
│  • dim_* : dimension tables (securities, counterparties, funds) │
│  • fct_* : fact tables (returns, transactions, positions)       │
│  • rpt_* : pre-aggregated report-level tables                   │
│  • All Soda-checked and Atlan-catalogued                        │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│              CONSUMPTION LAYER                                  │
│  • Power BI (investment performance, risk, operational reports) │
│  • Direct SQL access (analysts via Snowflake worksheets)        │
│  • Downstream APIs (risk system, external reporting tools)      │
│  • Excel add-in via Snowflake ODBC (for portfolio teams)        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Cloud Infrastructure

AIMCo's data platform is hosted on **Microsoft Azure**:

| Component | Azure Service |
|-----------|--------------|
| Data warehouse | Snowflake on Azure (Canada Central region) |
| Distributed compute | Azure Databricks |
| File storage | Azure Data Lake Storage Gen2 (ADLS) |
| Secret management | Azure Key Vault |
| Source control & CI/CD | Azure DevOps |
| Identity & access | Azure Active Directory (AAD) |
| Monitoring | Azure Monitor + custom Databricks logs |

All data stays within Canada (ADLS and Snowflake in Canada Central) to satisfy the data residency requirements of AIMCo's Canadian public-sector mandate.

---

## Snowflake Architecture Details

### Warehouse Strategy

Snowflake virtual warehouses are provisioned per workload type to control cost and prevent resource contention:

| Warehouse | Size | Purpose |
|-----------|------|---------|
| `INGESTION_WH` | Large | Bronze layer loads; runs during nightly ingestion window |
| `TRANSFORM_WH` | Medium | dbt runs (CI and production) |
| `DEV_WH` | X-Small | Developer sandbox queries; auto-suspend 60s |
| `REPORTING_WH` | Medium | Power BI and analyst queries; auto-suspend 300s |
| `ADMIN_WH` | X-Small | DBA tasks and maintenance |

All warehouses auto-suspend when idle. **Never run large ad-hoc queries on `REPORTING_WH`** — it delays report refreshes for investment teams.

### Database and Schema Layout

```
RAW_DB
  ├── BLOOMBERG/          (market prices, fundamentals)
  ├── FACTSET/            (earnings data, estimates)
  ├── PORTFOLIO_MGMT/     (IBOR feeds)
  ├── RISK_SYSTEM/        (VaR, attribution)
  └── FINANCE_ERP/        (GL, expenses)

INTERMEDIATE_DB
  ├── STAGING/            (stg_* models, one per source table)
  └── INTERMEDIATE/       (int_* models, cross-source joins)

ANALYTICS_DB
  ├── INVESTMENTS/        (fct_returns, dim_fund, dim_security)
  ├── RISK/               (fct_var, fct_attribution)
  ├── FINANCE/            (fct_expenses, rpt_fund_financials)
  └── REFERENCE/          (dim_counterparty, dim_currency)
```

---

## Databricks Architecture

Databricks is used for:
1. **Ingestion jobs**: PySpark notebooks that read from ADLS and write to Snowflake Bronze
2. **Orchestration**: Databricks Workflows sequences the entire daily pipeline
3. **Heavy compute**: Complex Python logic, ML models, and large joins that benefit from Spark

### Cluster strategy

| Cluster | Type | Purpose |
|---------|------|---------|
| `DATA_TEAM_SHARED` | Interactive (all-purpose) | Development and ad-hoc exploration |
| `INGEST_JOB_CLUSTER` | Job cluster (auto-created) | Nightly ingestion; created per-run, deleted after |
| `ML_CLUSTER` | Interactive (GPU) | ML prototyping; requires manager approval |

Job clusters are preferred for production — they start fresh each run, preventing state bleed between executions.

---

## dbt Project Structure

```
dbt-platform/
├── models/
│   ├── staging/
│   │   ├── bloomberg/       stg_bloomberg__prices.sql, stg_bloomberg__fundamentals.sql
│   │   ├── factset/
│   │   ├── portfolio_mgmt/
│   │   └── _sources.yml     source declarations
│   ├── intermediate/
│   │   ├── investments/     int_portfolio__calculated_returns.sql
│   │   └── risk/
│   └── marts/
│       ├── investments/     fct_portfolio_returns.sql, dim_fund.sql
│       ├── risk/
│       └── finance/
├── tests/                   custom data tests
├── macros/                  reusable SQL macros
├── checks/                  Soda quality check YAML files (mirrors models/)
├── analyses/                one-off analytical queries (not materialized)
├── dbt_project.yml
└── packages.yml
```

---

## CI/CD Pipeline (Azure Pipelines)

```
PR opened
    │
    ├─► dbt compile (catch missing refs and syntax errors)
    ├─► sqlfluff lint (enforce SQL style)
    ├─► dbt test --select state:modified+ (test changed models + dependents)
    └─► soda scan --dev (quality checks on dev Snowflake copy)

PR merged to main
    │
    ├─► dbt run --select state:modified+ (production Snowflake)
    ├─► dbt test (full test suite)
    ├─► soda scan --production
    ├─► dbt docs generate → push manifest to Atlan
    └─► Power BI dataset refresh (REST API call)
```

---

## Monitoring and Alerting

| What is monitored | Tool | Alert destination |
|------------------|------|------------------|
| Pipeline job failures | Databricks Workflows | `#data-platform-alerts` (Teams) |
| Soda quality check failures | Soda Cloud | `#data-platform-alerts` + on-call PagerDuty |
| Snowflake credit usage > threshold | Azure Monitor | Data Platform Lead |
| Stale data (freshness checks) | Soda | `#data-platform-alerts` |
| Atlan lineage sync failures | Atlan webhooks | `#data-governance` |

The on-call rotation is managed in PagerDuty and rotates weekly among senior data developers and data engineers.

---

## Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Transformation layer | dbt | SQL-native, version-controlled, auto-generates documentation and lineage |
| Compute separation | Databricks for complex Python/Spark, Snowflake for SQL | Right tool for right job; avoids over-engineering simple SQL in Spark |
| Orchestration | Databricks Workflows | Already in the stack; avoids adding a separate orchestration tool |
| Data catalog | Atlan | Deep integration with both dbt and Snowflake; supports classification and lineage in one place |
| Quality framework | Soda | Code-based checks version-controlled alongside dbt; integrates with CI/CD |
| Cloud provider | Azure | Existing enterprise agreement and identity integration via Azure AD |
