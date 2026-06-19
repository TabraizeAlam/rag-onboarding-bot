# Tools and Access Guide

This page describes every tool the Data Platform team uses, what it's for, and how to get access.

---

## Snowflake — Cloud Data Warehouse

**What it is:** Snowflake is Meridian's central data warehouse. All Bronze, Silver, and Gold layer data lives here. It is the authoritative source for investment analytics, reporting, and downstream data products.

**How to access:**
- URL: `meridian.snowflakecomputing.com` (requires VPN or corporate network)
- Login: Azure AD SSO with your @meridian.ca account
- Default role: `DATA_DEVELOPER_ROLE` (provisioned on Day 1)

**Key features used at Meridian:**
- **Time Travel**: query data as it was at any point in the last 90 days — critical for debugging pipeline issues and reprocessing
- **Data Sharing**: securely share curated Gold-layer datasets with external parties (auditors, consultants) without copying data
- **Tasks & Streams**: used for change-data-capture (CDC) patterns on source tables
- **Snowpipe**: continuous ingestion for real-time market data feeds

**Who to contact:** #data-platform-team on Teams, or raise an IT ticket for role/access issues.

---

## Databricks — Distributed Compute Platform

**What it is:** Databricks is used for workloads that require distributed processing (PySpark), ML model training, or complex Python logic that doesn't fit in pure SQL. Hosted on Azure.

**How to access:**
- Workspace URL provided by your team lead on Day 1
- Login: Azure AD SSO
- Do not create personal clusters — use `DATA_TEAM_SHARED` for dev work

**Key uses at Meridian:**
- **File-based ingestion**: loading vendor CSV/XML/JSON files from Azure Blob Storage into Snowflake Bronze
- **Complex transformations**: risk calculations, return attribution, and large joins that benefit from Spark's parallelism
- **Orchestration**: Databricks Workflows schedules and sequences the entire daily pipeline run
- **ML & experimentation**: notebooks for data science exploratory work and model prototyping

**Important:** All production code must live in Azure DevOps — never in Databricks notebooks unless the notebook is version-controlled via the Databricks-DevOps integration.

---

## dbt (data build tool) — Transformation Layer

**What it is:** dbt is the primary tool for building SQL-based data transformations in the Silver and Gold layers. It brings software engineering practices (version control, testing, documentation) to SQL.

**How to access:** dbt Core is installed locally (`pip install dbt-snowflake`). dbt Cloud is not used — all runs happen locally (dev) or via Azure Pipelines (CI/CD).

**Key concepts:**
- **Models**: `.sql` files in `models/` that define a SELECT statement. dbt handles the CREATE/INSERT.
- **Sources**: raw tables in the Bronze layer, declared in `sources.yml`
- **Tests**: built-in (`not_null`, `unique`, `accepted_values`) and custom tests in the `tests/` directory
- **Docs**: `dbt docs generate && dbt docs serve` creates a browsable data dictionary from your models and `.yml` descriptions
- **Lineage**: dbt automatically tracks which models depend on which — visible in the DAG view in dbt docs

**Common commands:**
```bash
dbt run                          # run all models
dbt run --select staging.*       # run only staging models
dbt run --select +fct_portfolio_returns  # run model and all upstream dependencies
dbt test                         # run all tests
dbt docs generate && dbt docs serve    # browse the data catalog locally
```

---

## Atlan — Data Catalog & Governance

**What it is:** Atlan is the team's metadata platform. It provides a searchable catalog of all data assets, tracks lineage (where did this data come from?), manages ownership, and enforces classification policies.

**How to access:** `meridian.atlan.com` — SSO login. Request to be added to the `Data Platform` workspace from the #data-governance channel.

**What you must do in Atlan:**
1. **Before building**: search Atlan to check if the data you need already exists as a certified Gold asset.
2. **After building**: ensure your new dbt models appear in Atlan (synced automatically via `dbt docs generate` in CI). Add a business description, assign an owner, and set the data domain.
3. **Classify sensitive data**: any model containing PII, financial personal data, or confidential investment positions must be tagged with the appropriate classification label. See the Data Classification Policy (linked in Atlan's home page).

**Lineage in Atlan:** Atlan auto-discovers lineage from dbt manifests and Databricks job logs. If lineage looks broken, run `dbt docs generate` in the CI pipeline and the sync job will update it within the hour.

---

## Soda — Data Quality Platform

**What it is:** Soda provides automated data quality monitoring. Every Gold-layer model has a set of Soda checks that run after each pipeline execution. Results are visible in Soda Cloud and failures alert the on-call engineer.

**How to access:** `cloud.soda.io` — ask your team lead to add you to the `Meridian Data Platform` organization.

**Writing checks:**
Checks live in the `checks/` directory of the `dbt-platform` repo, mirroring the `models/` directory structure. File naming: `<model_name>.yml`.

```yaml
checks for fct_portfolio_returns:
  - missing_count(return_date) = 0:
      name: Return date must always be populated
  - duplicate_count(portfolio_id, return_date) = 0:
      name: No duplicate portfolio-date combinations
  - freshness(loaded_at) < 1d:
      name: Data must be refreshed within last 24 hours
```

**SLA:** Gold-layer Soda checks must pass by 7:00 AM MT daily so that investment teams can trust the data when they start their day.

---

## Power BI — Business Intelligence & Reporting

**What it is:** Power BI is the standard reporting and dashboard tool for investment and operations teams. Data developers build and maintain the semantic models (datasets) that Power BI reports connect to.

**How to access:**
- Power BI Desktop: install from Microsoft Store
- Power BI Service: `app.powerbi.com` — request a Pro license via IT Service Desk

**Data connection:**
Power BI connects to Snowflake Gold-layer tables directly using DirectQuery or Import mode, depending on the report's refresh requirements. Use the `REPORTING_ROLE` in Snowflake for all Power BI connections — it has read-only access to `ANALYTICS_DB.*`.

**Semantic model ownership:** The Data Platform team owns and publishes semantic models (datasets) to the `Data Platform` workspace in Power BI Service. Business teams build their own reports on top of these shared datasets. Do not allow business teams to connect directly to Silver or Bronze layers.

---

## Azure DevOps — Source Control & CI/CD

**What it is:** All code (dbt models, Databricks notebooks, Python ingestion scripts, Soda checks) lives in Azure DevOps Repos. CI/CD pipelines are also defined here as YAML pipeline files.

**URL:** `dev.azure.com/meridian`

**Branching strategy:**
- `main` — production-ready code; direct commits not allowed
- `dev` — integration branch; PRs from feature branches merge here first in some team workflows
- `feature/<ticket-id>-<short-description>` — your working branch

**CI pipeline (runs on every PR):**
1. `dbt compile` — catches SQL syntax errors and missing refs
2. `dbt test --select state:modified+` — runs tests on changed models and their dependents
3. Soda scan on affected models using a dev Snowflake warehouse
4. SQLFluff lint check

**CD pipeline (runs on merge to main):**
1. `dbt run --select state:modified+` on production Snowflake
2. Full `dbt test` run
3. Soda production scan
4. Databricks workflow redeploy if any notebook changed
5. Power BI dataset refresh triggered via REST API

---

## Teams Channels (Microsoft Teams)

| Channel | Purpose |
|---------|---------|
| `#data-platform-team` | General team discussion, daily standups |
| `#data-platform-alerts` | Automated pipeline failure alerts (do not post here manually) |
| `#data-governance` | Atlan questions, classification policies, data ownership |
| `#data-platform-help` | Questions from business users about data and reports |
| `#business-transformation` | Cross-team updates on the BTP program |
