# Deployment Process

## Overview

All production deployments go through GitHub Actions CI/CD pipelines. There are no manual deployments to production. Every merge to `main` triggers a deployment to staging automatically; production deployments require a manual approval gate.

## Environments

| Environment | Branch | URL | Auto-deploy? | Approval needed? |
|-------------|--------|-----|--------------|-----------------|
| Development | feature/* | `dev-<service>.internal.acme.com` | No | No |
| Staging | main | `staging-<service>.acme.com` | Yes (on merge) | No |
| Production | main (tagged) | `<service>.acme.com` | No | Yes — two approvers |

## Deployment Pipeline Steps

1. **Lint & Test** — ESLint, Pylint, unit tests must pass. Coverage must be ≥ 80%.
2. **Build** — Docker image built and pushed to ECR (`123456789.dkr.ecr.us-west-2.amazonaws.com/acme/<service>`).
3. **Security Scan** — Trivy scans the image for HIGH/CRITICAL CVEs. Pipeline fails if any are found.
4. **Deploy to Staging** — Image deployed to `acme-staging` EKS cluster via Helm.
5. **Smoke Tests** — Automated smoke tests run against staging. Must pass before production gate opens.
6. **Manual Approval** — Two engineers (at least one senior) approve in GitHub Actions.
7. **Deploy to Production** — Rolling update to `acme-prod` EKS cluster. Max surge: 25%, max unavailable: 0%.
8. **Post-deploy Health Check** — Datadog synthetic monitors verify the service is healthy for 5 minutes.

## How to Deploy

### Standard deployment
```bash
# 1. Merge your PR to main (triggers staging auto-deploy)
# 2. Verify staging looks good
# 3. Create a release tag
git tag v1.2.3 -m "Release v1.2.3: [brief description]"
git push origin v1.2.3
# 4. Go to GitHub Actions → the release workflow → approve the production step
```

### Hotfix deployment
For P0/P1 incidents only:
```bash
git checkout -b hotfix/fix-description
# make fix, get review from on-call engineer
git push origin hotfix/fix-description
# Open PR directly to main with [HOTFIX] prefix in title
# Tag immediately after merge
```

## Rollback

If a production deploy causes issues:
```bash
# Via Helm (fastest)
helm rollback <service-name> -n production

# Or redeploy previous image tag via GitHub Actions
# Go to Actions → Re-run the previous successful deploy workflow
```

Always post in #incidents when rolling back and open an incident ticket.

## Kubernetes Basics

Cluster access is via `kubectl`. Ensure your kubeconfig is configured:
```bash
aws eks update-kubeconfig --name acme-prod --region us-west-2 --profile acme-dev
```

Useful commands:
```bash
kubectl get pods -n <namespace>
kubectl logs -f <pod-name> -n <namespace>
kubectl describe pod <pod-name> -n <namespace>
kubectl rollout status deployment/<service> -n <namespace>
```

## Deployment Freeze Windows

No production deployments during:
- Fridays after 2 PM PT through Monday 9 AM PT
- 2 weeks before and during major product launches
- December 20 – January 2 (holiday freeze)

Freeze dates are posted in #eng-announcements and the shared Eng Calendar.

## Monitoring After Deployment

After every production deploy, monitor:
- Datadog dashboard: `acme.datadoghq.com/dashboard/prod-overview`
- Error rate in Datadog APM (should be < 0.1% for p99)
- Latency (p99 should not increase > 20% vs. 7-day baseline)
- Slack alerts in #prod-alerts

If error rate spikes, rollback immediately and open an incident.
