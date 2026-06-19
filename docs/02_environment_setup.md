# Developer Environment Setup

This guide walks a new Data Platform team member through setting up their local development environment and getting access to the core tools.

## Prerequisites

Before your first day, IT should have provisioned:
- Azure AD account (your @aimco.ca login)
- Laptop with Windows 11 and admin rights for software installation
- VPN client (GlobalProtect) — required for connecting to on-premise systems

If any of these are missing, contact the IT Service Desk (servicedesk@aimco.ca or Teams: IT Help).

---

## Step 1: Install Core Tools

Install the following on your local machine:

```
Python 3.11+        → python.org/downloads
Git                 → git-scm.com
VS Code             → code.visualstudio.com
Azure Data Studio   → Optional but useful for Snowflake SQL
Power BI Desktop    → Microsoft Store or aka.ms/pbidesktopdl
dbt Core            → pip install dbt-snowflake
```

### Recommended VS Code Extensions
- Python (Microsoft)
- dbt Power User (dbt-labs)
- SQLFluff (SQL linting)
- GitLens
- Azure Repos

---

## Step 2: Snowflake Access

Snowflake is AIMCo's cloud data warehouse — the single source of truth for all curated data.

**Account URL:** `aimco.snowflakecomputing.com` (internal; requires VPN)

**Authentication:** Single Sign-On via Azure AD. Use the "Sign in with SSO" option and enter your @aimco.ca email.

**Your default role:** `DATA_DEVELOPER_ROLE` — gives read access to all Bronze/Silver schemas and read/write to the `DEV_` schemas for development work.

**Production write access** requires a separate `DATA_ENGINEER_PROD_ROLE` — request via the Access Management portal (MyAccess) after your 30-day probation period.

### Snowflake Databases and Schemas

| Database | Purpose |
|----------|---------|
| `RAW_DB` | Bronze layer — raw ingested data, no transformations |
| `INTERMEDIATE_DB` | Silver layer — cleaned and joined models |
| `ANALYTICS_DB` | Gold layer — business-ready data marts |
| `DEV_<YOUR_NAME>_DB` | Personal development sandbox |

---

## Step 3: Databricks Workspace

Databricks is used for heavy compute tasks: ingestion of large market data files, PySpark transformations, and ML workloads.

**Workspace URL:** `adb-xxxxxx.azuredatabricks.net` (shared via your team lead on Day 1)

**Authentication:** Azure AD SSO — same credentials as Snowflake.

**Clusters:** Do not create personal clusters without approval — use the shared `DATA_TEAM_SHARED` cluster for development. Production jobs run on job clusters provisioned by the platform team.

### First-time Databricks setup

1. Log in via the workspace URL.
2. Navigate to **User Settings → Access Tokens** and generate a personal access token (PAT). Store this in Azure Key Vault (ask your team lead for the vault name).
3. Install the Databricks CLI locally:

```bash
pip install databricks-cli
databricks configure --token
# Enter workspace URL and your PAT when prompted
```

---

## Step 4: dbt Setup

dbt is used for all SQL transformations in the Silver and Gold layers.

### Clone the data platform repository

```bash
git clone https://aimco-devops@dev.azure.com/aimco/DataPlatform/_git/dbt-platform
cd dbt-platform
```

### Configure your dbt profile

Create `~/.dbt/profiles.yml`:

```yaml
data_platform:
  target: dev
  outputs:
    dev:
      type: snowflake
      account: aimco
      user: <your-email>@aimco.ca
      authenticator: externalbrowser   # uses Azure AD SSO
      role: DATA_DEVELOPER_ROLE
      warehouse: DEV_WH
      database: DEV_<YOUR_NAME>_DB
      schema: dbt_dev
      threads: 4
```

### Verify your setup

```bash
dbt debug        # should show all green
dbt compile      # compiles all models without running them
dbt run --select staging.*   # runs only staging models
```

---

## Step 5: Atlan (Data Catalog)

Atlan is the team's metadata and data governance platform.

**URL:** `aimco.atlan.com` (SSO login)

All data developers are expected to:
- Browse Atlan before starting new work to check if data assets already exist
- Add descriptions and ownership tags when creating new dbt models
- Flag data quality issues discovered in pipelines via Atlan's issue tracker

---

## Step 6: Soda Cloud (Data Quality)

Soda is used for automated data quality checks that run after each pipeline execution.

**URL:** `cloud.soda.io` — log in with your work email and ask your team lead to add you to the `AIMCo Data Platform` organization.

Your responsibility: write Soda checks (`.yml` files in the `checks/` directory of the dbt repo) for any new Silver or Gold models you create.

---

## Step 7: Azure DevOps

All code lives in Azure DevOps Repos. CI/CD pipelines are also defined there.

**URL:** `dev.azure.com/aimco`

Projects you need access to:
- `DataPlatform` — the main dbt and pipeline code
- `DataGovernance` — Soda checks and Atlan automation scripts

Request access via MyAccess with your manager's approval.

---

## Access Summary

| Tool | How to get access | Typical wait |
|------|------------------|-------------|
| Snowflake (read) | Provisioned on Day 1 by IT | Immediate |
| Databricks | Manager submits access request | 1-2 business days |
| Atlan | Slack #data-platform-team, tag @data-governance-lead | Same day |
| Soda Cloud | Ask team lead directly | Same day |
| Azure DevOps Repos | MyAccess portal | 1-2 business days |
| Power BI Service | IT Service Desk ticket | 1-2 business days |
