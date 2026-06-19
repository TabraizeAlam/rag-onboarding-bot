# Data Governance Framework

Data governance at AIMCo's Data Platform team ensures that data assets are trustworthy, discoverable, properly classified, and used responsibly. This page explains the key policies and tools every data developer must follow.

---

## Why Data Governance Matters at AIMCo

AIMCo manages approximately $160 billion in assets on behalf of public-sector beneficiaries — teachers, nurses, government employees, and other Albertans whose retirement savings depend on the accuracy of investment data. Errors in data can lead to incorrect performance reporting, misaligned investment decisions, and regulatory exposure. Governance is not bureaucracy — it is how we maintain trust with our clients and regulators.

---

## The Three Pillars

### 1. Data Catalog (Discoverability)
### 2. Data Quality (Reliability)
### 3. Data Classification (Protection)

---

## 1. Data Catalog — Atlan

**All data assets must be registered in Atlan.** No Silver or Gold model reaches production without a catalog entry.

### What must be documented for every model

| Field | Requirement |
|-------|------------|
| Name | Follows the dbt naming convention (`stg_`, `int_`, `fct_`, `dim_`) |
| Description | Plain English: what this model represents, its grain, and key caveats |
| Owner | The data developer responsible for the model's health |
| Domain | One of: Investments, Risk, Finance, Operations, Reference Data |
| Data Classification | See classification labels below |
| Lineage | Auto-populated from dbt manifest sync |
| Column descriptions | Required for all Gold-layer columns; recommended for Silver |

### How dbt models appear in Atlan

The CI/CD pipeline runs `dbt docs generate` on every merge to `main`. The resulting `manifest.json` and `catalog.json` are automatically pushed to Atlan via the Atlan-dbt integration. Descriptions and tests you define in `.yml` files become the Atlan metadata automatically — no manual entry required beyond what you write in code.

### Searching Atlan before building

Before creating a new model, search Atlan for:
1. Does the data I need already exist as a certified Gold asset? (Use the certified filter.)
2. Is there a Silver model I can build on top of?
3. Is there lineage I should extend rather than duplicate?

If you find a relevant asset but it's not quite right, open a ticket to discuss extending it rather than creating a parallel model.

---

## 2. Data Quality — Soda

Every model promoted to the Silver or Gold layer requires a **data quality contract** — a set of Soda checks that define what "correct" looks like for that model.

### Mandatory checks for Gold-layer models

```yaml
checks for <model_name>:
  # Completeness
  - missing_count(<primary_key_column>) = 0
  
  # Uniqueness
  - duplicate_count(<primary_key_columns>) = 0
  
  # Freshness (adjust threshold to match pipeline SLA)
  - freshness(loaded_at) < 24h
  
  # Row count sanity (prevents silent empty-table failures)
  - row_count > 0
```

### Domain-specific checks

For investment data, add range checks that catch obviously wrong values:

```yaml
checks for fct_portfolio_returns:
  - min(gross_return) >= -1.0:
      name: Returns cannot be below -100%
  - max(gross_return) <= 10.0:
      name: Flag daily returns above 1000% for review
  - missing_count(benchmark_return) = 0
```

### When Soda checks fail

1. An alert fires immediately to `#data-platform-alerts` in Teams.
2. The on-call data engineer investigates root cause.
3. If data is corrupted: the affected Gold table is quarantined — reports consuming it get a "data quality hold" banner in Power BI (managed via the semantic model).
4. A post-incident note is added to the model's Atlan page.

---

## 3. Data Classification

AIMCo handles data that varies significantly in sensitivity. Every data asset in the catalog must have one of the following classification labels:

| Label | Definition | Examples |
|-------|-----------|---------|
| `PUBLIC` | Publicly available information | Benchmark index returns, publicly disclosed AUM |
| `INTERNAL` | Non-sensitive business data | Aggregated portfolio metrics, team headcount |
| `CONFIDENTIAL` | Sensitive business data, restricted access | Fund-level performance, investment theses |
| `RESTRICTED` | Highest sensitivity; requires explicit approval | Individual beneficiary records, counterparty agreements, proprietary model parameters |

### Rules by classification

- `PUBLIC` and `INTERNAL`: accessible to all staff with a Snowflake account.
- `CONFIDENTIAL`: accessible via the `INVESTMENTS_CONFIDENTIAL_ROLE` only — request via MyAccess with manager and data governance lead approval.
- `RESTRICTED`: accessible only to explicitly named individuals — any new access request requires VP-level approval and is logged in the audit trail.

Data developers are responsible for classifying new models correctly. When uncertain, default to the higher classification and discuss with the Data Governance Lead.

---

## Data Lineage

Lineage tracks the path data takes from source through transformations to consumption. At AIMCo:

- **Intra-platform lineage**: auto-tracked by dbt's `{{ ref() }}` and `{{ source() }}` macros, visible in both dbt docs and Atlan.
- **Cross-system lineage**: if a Gold-layer table is consumed by an external system (e.g. a risk system, a reporting API), log it in the Atlan "consumers" section of that model.
- **Power BI lineage**: Atlan's Power BI connector discovers which Snowflake tables each dataset reads from, extending lineage all the way to the dashboard.

---

## Data Retention

| Layer | Default retention |
|-------|-----------------|
| Bronze | 5 years (regulatory requirement for investment data) |
| Silver | 3 years |
| Gold | 7 years (pension fund audit requirements) |

Retention is managed via Snowflake's Time Travel and Fail-safe, plus a scheduled purge job for old partitions. Do not manually delete data — raise a ticket if cleanup is needed.

---

## Requesting New Data Access

All data access is provisioned through the **MyAccess portal** (myaccess.aimco.ca):

1. Log in with your Azure AD credentials.
2. Search for the Snowflake role or Atlan workspace you need.
3. Select your manager as approver.
4. For `CONFIDENTIAL` or `RESTRICTED` data: the Data Governance Lead is automatically added as a second approver.

Access is reviewed and recertified quarterly. Unused roles are automatically revoked.
