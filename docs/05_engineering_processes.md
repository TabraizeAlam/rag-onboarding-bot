# Engineering Processes

## Code Review

All code changes require a pull request. Direct pushes to `main` are blocked.

### PR Requirements
- **At least 1 approval** from a team member (not the author).
- **2 approvals** required for: changes to CI/CD pipelines, Terraform infrastructure, shared libraries, or anything touching production secrets.
- All CI checks must pass (lint, tests, security scan) before merging.
- PR description must include: what changed, why, and how to test it.
- PRs should be small enough to review in under 30 minutes. Split large changes into stacked PRs.

### PR Title Convention
Use conventional commits format:
```
feat(scope): short description
fix(scope): short description
chore(scope): short description
docs(scope): short description
refactor(scope): short description
```
Example: `feat(auth): add OAuth2 PKCE flow for mobile clients`

### Code Review Etiquette
- Reviewers respond within 1 business day.
- Use "Request Changes" only for blockers. Suggestions and nits use comments.
- Authors respond to all review comments before merging, or explicitly resolve with a reason.
- Approvals are not rubber stamps — if you wouldn't feel comfortable owning this code, don't approve.

## Branching Strategy

We use **trunk-based development**:
- `main` — always deployable. Protected.
- `feature/<ticket-id>-short-description` — short-lived feature branches. Merge within 2 days of opening, or rebase frequently to avoid drift.
- `hotfix/<description>` — for P0/P1 production fixes only.

Delete branches after merging. Branch list cleanup runs weekly.

## Sprint Process

We run **2-week sprints** using Jira.

| Day | Event |
|-----|-------|
| Sprint start (Monday) | Sprint planning — commit to the sprint backlog |
| Wednesday (mid-sprint) | Optional mid-sprint sync — flag blockers early |
| Sprint end (Friday) | Sprint review (demo) + retrospective |
| Following Monday | Next sprint planning |

### Tickets
- Every piece of work needs a Jira ticket. No ticket = no work.
- Ticket sizes: XS (< 2h), S (half-day), M (1 day), L (2-3 days), XL (needs breakdown).
- XL tickets must be broken down before sprint planning.
- Update ticket status daily: To Do → In Progress → In Review → Done.

## Incident Management

### Severity Levels
| Severity | Description | Response Time | Examples |
|----------|-------------|---------------|---------|
| P0 | Production down, all users affected | 15 minutes | Site outage, data loss |
| P1 | Major feature broken, significant user impact | 30 minutes | Auth failures, checkout broken |
| P2 | Partial degradation, workaround exists | 4 hours | Slow queries, non-critical feature down |
| P3 | Minor issue, cosmetic | Next business day | UI glitch, minor latency increase |

### Incident Response Steps
1. **Detect** — alert fires in #prod-alerts or customer reports.
2. **Declare** — on-call engineer posts in #incidents: "Incident declared: [brief description]. P[severity]. I'm IC."
3. **Triage** — assess scope and severity. Pull in others if needed.
4. **Mitigate** — rollback, feature flag off, or hotfix.
5. **Resolve** — confirm metrics return to normal.
6. **Post-mortem** — written within 48 hours for P0/P1. Template in Confluence.

## Documentation Standards

- Every service has a `README.md` at the repo root covering: what it does, how to run locally, API surface, and owner.
- Architecture decisions are recorded as ADRs (Architecture Decision Records) in `/docs/adr/` within the repo.
- Runbooks live in Confluence under "Platform Engineering > Runbooks".
- Keep docs updated in the same PR as the code change. Outdated docs are treated as bugs.

## Testing Standards

- **Unit tests** — required for all business logic. Coverage ≥ 80% (enforced in CI).
- **Integration tests** — required for all API endpoints and database interactions.
- **End-to-end tests** — owned by QA for critical user flows.
- Tests must be deterministic. Flaky tests are P2 incidents and must be fixed or deleted within 1 sprint.
- No `sleep()` in tests. Use mocks or retry with backoff.
