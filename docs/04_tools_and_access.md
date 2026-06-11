# Tools and Access

## Access Request Process

All tool access is requested via the IT portal at `it.internal.acme.com`. Your manager must approve each request. Standard tools are auto-provisioned on day 1; specialized tools require justification.

Expected provisioning time: 1–2 business days for standard tools, up to 5 days for elevated access.

## Core Tools

### Communication
| Tool | Purpose | Access |
|------|---------|--------|
| Slack | Team chat, async communication | Auto-provisioned on day 1 |
| Zoom | Video meetings | Auto-provisioned on day 1 |
| Google Workspace | Email, Docs, Calendar | Auto-provisioned on day 1 |

Key Slack channels to join immediately:
- `#general` — company-wide announcements
- `#eng-announcements` — engineering-wide announcements
- `#team-general` — Platform Engineering team channel
- `#infra-team`, `#devex-team`, or `#data-platform` — your squad channel
- `#prod-alerts` — production alert notifications
- `#incidents` — active incident coordination
- `#help-desk` — IT support requests

### Development
| Tool | Purpose | Access |
|------|---------|--------|
| GitHub (acme-corp org) | Source code, PRs, CI/CD | Request via IT portal → "GitHub Org Access" |
| AWS Console | Cloud infrastructure | Request via IT portal → "AWS SSO" |
| Docker Desktop | Local containerization | Download from IT software portal |
| Datadog | Monitoring and APM | Request via IT portal → "Datadog Read" (default) or "Datadog Admin" |
| Terraform Cloud | Infrastructure state | Request via IT portal → "Terraform Cloud" |
| ArgoCD | GitOps CD dashboard | `argocd.internal.acme.com` — SSO login |

### Project Management
| Tool | Purpose | Access |
|------|---------|--------|
| Jira | Sprint tracking, tickets | Auto-provisioned on day 1 |
| Confluence | Internal documentation | Auto-provisioned on day 1 |
| Notion | Team notes, lightweight docs | Request via IT portal |
| Figma | Design files | Request via IT portal (engineers: Viewer role) |

### Data and Analytics
| Tool | Purpose | Access |
|------|---------|--------|
| Snowflake | Analytics data warehouse | Request via IT portal → "Snowflake Read" |
| dbt Cloud | Data transformations | Request via IT portal → "dbt Cloud" |
| Looker | Business intelligence dashboards | Request via IT portal → "Looker Viewer" |
| Airflow | Data pipeline orchestration | `airflow.internal.acme.com` — request via IT portal |

## Elevated Access

The following require additional justification and manager + security approval:

- **Production database access** — for break-glass incidents only. Documented in the incident ticket. Access is time-limited (4 hours max).
- **Terraform Admin** — only for Infra Squad leads.
- **AWS root/admin** — not available. Use least-privilege IAM roles.
- **Datadog Admin** — for on-call engineers and squad leads.

## On-call Rotation

The team runs a weekly on-call rotation covering production incidents:
- Schedule is managed in PagerDuty (`acme.pagerduty.com`)
- You will be added to the rotation after your first 60 days
- On-call runbooks are in Confluence under "Platform Engineering > On-Call Runbooks"
- Escalation path: On-call engineer → Squad Lead → Engineering Manager → VP of Engineering

## Secrets and Credentials

- **Never store secrets in code or environment files committed to git.** Pre-commit hooks will catch this.
- All application secrets live in AWS Secrets Manager under `/acme/<environment>/<service>/<secret-name>`.
- Local development uses `.env` files (not committed). Copy from `.env.example` in each repo.
- Personal credentials (tokens, keys) should be stored in 1Password (team license — request via IT portal).
- API keys for third-party services are managed by the Infra Squad. Request via #infra-team.

## VPN

Production internal services require VPN. We use Tailscale:
1. Download Tailscale from `it.internal.acme.com/software`
2. Sign in with your Acme Google account
3. You will be auto-enrolled in the `acme-engineers` network once approved by IT

VPN is required to access: ArgoCD, Airflow, internal Confluence spaces, and staging environments.
