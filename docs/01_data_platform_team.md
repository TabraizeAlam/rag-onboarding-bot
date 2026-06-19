# Data Platform Team — Overview

## About Meridian

Meridian Investment Management Corporation (Meridian) is a Crown corporation of the Province of Alberta. Meridian manages investment funds on behalf of approximately 30 Alberta public sector pension, endowment, and government fund clients — including teachers, nurses, and other public service workers across the province. As of the most recent annual report, Meridian manages approximately $160 billion in assets under management (AUM).

Meridian's headquarters is in Edmonton, Alberta, with additional offices in Calgary, New York, London, and Luxembourg. Investment activities span public equities, fixed income, private equity, real estate, infrastructure, and private credit.

Source: Meridian Annual Report and corporate website (meridianinvestments.ca).

## The Data & Analytics Team

The Data & Analytics team sits within Meridian's Technology and Operations division. The team's mandate is to build, maintain, and evolve the Enterprise Data Platform that serves investment and operational decision-making across the organization.

### What the team does

- **Pipeline engineering**: Building and maintaining data ingestion pipelines from investment systems, market data vendors, and operational sources into the central data platform.
- **Analytics engineering**: Transforming raw data into trusted, documented data models that analysts and portfolio teams can rely on.
- **Data governance**: Cataloguing data assets, enforcing data quality standards, and managing metadata so teams can find and trust the data they use.
- **Self-service reporting**: Enabling business teams to build their own Power BI dashboards on top of curated data marts.
- **Platform operations**: Managing the health, performance, and cost of the Snowflake and Databricks environments.

### Business Transformation Program

Meridian is in the midst of a multi-year Business Transformation Program aimed at modernizing its technology and data infrastructure. The Data Platform team is a key delivery team for this program — migrating from legacy systems to a modern cloud-native data stack built on Snowflake, Databricks, and dbt.

## Team Roles

| Role | Responsibilities |
|------|-----------------|
| Senior Data Developer | Pipeline architecture, dbt model design, code reviews, mentoring |
| Data Engineer | Ingestion pipelines, Databricks notebooks, orchestration |
| Analytics Engineer | dbt models, data marts, documentation, stakeholder alignment |
| Data Analyst | SQL analysis, Power BI reports, ad hoc data requests |
| Data Governance Lead | Atlan catalog, data classification, lineage, ownership policies |
| Platform Engineer | Snowflake administration, Databricks clusters, cost optimization |

## Key Stakeholders

- **Investment teams** (Public Equities, Fixed Income, Real Assets, Private Equity): primary consumers of curated data marts and performance reports.
- **Finance & Risk**: consumers of portfolio analytics data; heavy Power BI users.
- **Enterprise Architecture**: governs technology standards; the data team coordinates with EA on new tool adoption.
- **Compliance & Legal**: works with the data governance team on data classification and retention policies.

## Team Norms

- All data assets must be registered in Atlan before being promoted to the Gold layer.
- New pipelines require a data quality contract (Soda checks) before going to production.
- Code reviews are mandatory for all dbt model changes — minimum one senior approval.
- Team standups: Monday/Wednesday/Friday at 9:30 AM MT on Teams.
- Backlog managed in Azure DevOps (Boards).
