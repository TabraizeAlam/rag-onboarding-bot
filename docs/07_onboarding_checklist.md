# New Hire Onboarding Checklist — Data Platform Team

Welcome to the Meridian Data Platform team! This checklist guides you through your first four weeks. Work through it in order — each week builds on the last.

---

## Before Day 1 (done by your manager or IT)

- [ ] Azure AD account (@meridian.ca) created
- [ ] Laptop provisioned with Windows 11
- [ ] VPN (GlobalProtect) configured
- [ ] Snowflake `DATA_DEVELOPER_ROLE` provisioned
- [ ] Azure DevOps Repos access granted to `DataPlatform` project
- [ ] Microsoft Teams set up and added to relevant channels
- [ ] Meeting invitation sent for onboarding buddy introduction
- [ ] Week 1 calendar blocked with onboarding sessions

---

## Week 1 — Orientation and Access

### Day 1 (Monday)
- [ ] Complete HR paperwork and laptop security setup (bitlocker, MDE, Intune enrollment)
- [ ] Activate @meridian.ca account and set up MFA
- [ ] Join Teams channels: `#data-platform-team`, `#data-governance`, `#data-platform-help`, `#business-transformation`
- [ ] Meet your **onboarding buddy** (assigned by your manager) — first 1:1 on Day 1
- [ ] Get your onboarding buddy's contact and calendar

### Day 1-2: Environment Setup
- [ ] Install core tools: Python 3.11, Git, VS Code, dbt, Databricks CLI (see [02_environment_setup.md])
- [ ] Connect to Snowflake via SSO — verify you can query `RAW_DB`
- [ ] Log in to Databricks workspace
- [ ] Log in to Atlan and explore the catalog
- [ ] Log in to Soda Cloud
- [ ] Access Azure DevOps and clone the `dbt-platform` repository

### Day 2-3: Platform Orientation
- [ ] Read [06_platform_architecture.md] — understand the full Medallion architecture
- [ ] Read [03_data_pipeline_workflow.md] — understand how a pipeline goes from idea to production
- [ ] Browse Atlan — explore 5–10 Gold-layer assets and read their descriptions
- [ ] Run `dbt debug` locally to verify your local dbt setup
- [ ] Run `dbt compile` — ensure all 300+ models compile without errors

### Day 3-5: Codebase Orientation
- [ ] Walk through the `dbt-platform` repo structure with your onboarding buddy
- [ ] Identify 2–3 existing Gold-layer models in your domain and trace them back to Bronze in Atlan
- [ ] Read 3 merged PRs in Azure DevOps to understand the team's code review style
- [ ] Attend your first team standup and introduce yourself

---

## Week 2 — First Contribution

### Goal: your first PR merged to `dev`

- [ ] Request any additional access needed (Databricks, Soda, Power BI Service) via MyAccess
- [ ] Pick up a "good first issue" ticket from Azure DevOps Boards (ask your manager)
- [ ] Implement the change on a feature branch using the naming convention `feature/<ticket-id>-<description>`
- [ ] Write a dbt test for any new column you introduce
- [ ] Run `dbt test --select <your_model>` locally before opening a PR
- [ ] Open a PR, link it to the Azure DevOps ticket, and request review from your onboarding buddy
- [ ] Address review comments and get the PR merged
- [ ] Write a Soda check for your new model (if Silver or Gold layer) in `checks/`

### Shadow sessions this week
- [ ] Shadow a Senior Data Developer during a production pipeline run review
- [ ] Sit in on one stakeholder data request meeting (ask your manager to include you)

---

## Week 3 — Domain Deepening

### Goal: understand the investment domain context

- [ ] Read Meridian's most recent Annual Report (available at meridianinvestments.ca) — focus on:
  - Investment framework and asset classes
  - Performance reporting methodology
  - Client fund descriptions
- [ ] Schedule a 30-minute intro meeting with one investment analyst who consumes your team's data
- [ ] Review the Power BI reports your team's Gold models power — understand what each report is answering for the business
- [ ] Complete Meridian's mandatory Information Security Awareness training (assigned in your Learning portal)
- [ ] Complete the Data Classification Policy training (assigned by your manager)

### Technical deepening
- [ ] Run the full `dbt` model suite locally and understand the DAG structure from `dbt docs serve`
- [ ] Write and run a Soda check scan locally against your DEV Snowflake schema
- [ ] Review at least one Databricks ingestion notebook end-to-end with your buddy
- [ ] Understand how a failed Soda check triggers a Teams alert (your buddy will simulate one for you)

---

## Week 4 — Independence

### Goal: complete an end-to-end task independently

- [ ] Take ownership of a medium-complexity ticket (new Bronze-to-Gold pipeline for an existing source)
- [ ] Design the model structure, get a quick sync with your buddy before coding
- [ ] Implement Bronze ingestion (if needed), Silver staging, and Gold mart models
- [ ] Add dbt tests and Soda checks
- [ ] Open a PR and present the design briefly in the PR description
- [ ] Document the new model in Atlan after merge (add description, owner, domain, classification)
- [ ] Demo the new data to the business stakeholder who requested it

### End-of-month check-in
- [ ] 1:1 with your manager: review what went well, what was confusing, what you want to learn next
- [ ] Update your Azure DevOps user profile with your team and skills
- [ ] Add your preferred contact method to the team wiki

---

## Ongoing Responsibilities

Once settled in, every data developer on the team is responsible for:

| Responsibility | Frequency |
|---------------|-----------|
| Attend standups | Mon / Wed / Fri, 9:30 AM MT |
| Monitor `#data-platform-alerts` | Daily (during business hours) |
| Review PRs assigned to you | Within 1 business day |
| Update ticket status in DevOps Boards | As work progresses |
| Recertify data access | Quarterly (prompted by MyAccess) |
| Keep Atlan descriptions current for models you own | When models change |
| Add Soda checks for new models | Before every production promotion |

---

## Key Contacts

| Role | Who to contact |
|------|---------------|
| Manager / Team Lead | Your direct manager (see your org chart in Teams) |
| Onboarding Buddy | Assigned on Day 1 |
| IT Service Desk | `servicedesk@meridian.ca` or IT Help channel in Teams |
| Data Governance Lead | `#data-governance` channel |
| Databricks / Platform issues | `#data-platform-team` channel |
| HR / Payroll | HR Connect portal |

---

## Quick Reference: Where Does Everything Live?

| What | Where |
|------|-------|
| Code (dbt, notebooks, scripts) | Azure DevOps Repos — `DataPlatform` project |
| Work tickets and backlog | Azure DevOps Boards |
| Data catalog and lineage | Atlan (`meridian.atlan.com`) |
| Data quality checks | Soda Cloud + `checks/` folder in dbt repo |
| Reports and dashboards | Power BI Service (`app.powerbi.com`) |
| Data warehouse (SQL) | Snowflake (`meridian.snowflakecomputing.com`) |
| Compute (PySpark, notebooks) | Databricks workspace |
| Team communication | Microsoft Teams |
| HR, access requests | MyAccess portal + HR Connect |
