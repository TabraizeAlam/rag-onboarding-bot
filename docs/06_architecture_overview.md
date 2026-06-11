# Architecture Overview

## System Architecture

Acme Corp's platform is a microservices architecture running on AWS, orchestrated with Kubernetes (EKS). Services communicate via REST APIs and async events (Kafka).

## High-Level Diagram

```
                        ┌──────────────────────────────┐
                        │         API Gateway           │
                        │  (Kong, us-west-2, HA x3)    │
                        └────────────┬─────────────────┘
                                     │
              ┌──────────────────────┼───────────────────────┐
              │                      │                       │
    ┌─────────▼──────┐    ┌──────────▼──────┐    ┌──────────▼──────┐
    │  Auth Service  │    │  Product Service │    │  Order Service  │
    │  (Python/FastAPI)│  │  (Node.js/Express)│   │  (Go/Gin)       │
    └─────────┬──────┘    └──────────┬──────┘    └──────────┬──────┘
              │                      │                       │
    ┌─────────▼──────┐    ┌──────────▼──────┐    ┌──────────▼──────┐
    │  PostgreSQL    │    │  PostgreSQL +    │    │  PostgreSQL +   │
    │  (RDS, Multi-AZ)│  │  Redis Cache    │    │  Kafka Events   │
    └────────────────┘    └─────────────────┘    └─────────────────┘
```

## Core Services

### Auth Service
- **Language:** Python 3.11 / FastAPI
- **Repo:** `github.com/acme-corp/auth-service`
- **Responsibility:** Authentication (OAuth2/OIDC), authorization (RBAC), session management.
- **Database:** PostgreSQL (RDS) — users, roles, sessions tables.
- **Owner:** DevEx Squad
- **Port:** 8081 (internal), exposed via API Gateway at `/api/auth/*`

### Product Service
- **Language:** Node.js 20 / Express
- **Repo:** `github.com/acme-corp/product-service`
- **Responsibility:** Product catalog, inventory, pricing.
- **Database:** PostgreSQL + Redis for catalog caching (TTL: 5 minutes).
- **Owner:** Product Squad (not Platform Engineering — we support infrastructure only)
- **Port:** 8082 (internal)

### Order Service
- **Language:** Go 1.22 / Gin
- **Repo:** `github.com/acme-corp/order-service`
- **Responsibility:** Order creation, payment processing orchestration, fulfillment triggers.
- **Database:** PostgreSQL for orders + Kafka for async events to fulfillment.
- **Owner:** Commerce Squad
- **Port:** 8083 (internal)

### Data Pipeline Service
- **Language:** Python 3.11 / Apache Airflow
- **Repo:** `github.com/acme-corp/data-pipelines`
- **Responsibility:** ETL from operational DBs to Snowflake data warehouse.
- **Schedule:** Hourly incremental loads, daily full refreshes at 2 AM PT.
- **Owner:** Data Platform Squad

## Infrastructure

### Cloud Provider
AWS (primary), us-west-2 region. DR failover region: us-east-1 (active-passive, RTO: 2 hours, RPO: 1 hour).

### Kubernetes Clusters
- `acme-prod` — production workloads. 3 AZs, auto-scaling node groups.
- `acme-staging` — staging/pre-prod. Single AZ, fixed size.
- `acme-tools` — internal tooling (ArgoCD, monitoring stack, build runners).

Cluster configs are managed via Terraform in `github.com/acme-corp/infra`.

### Networking
- VPC with private subnets for all services.
- Public subnets only for API Gateway and load balancers.
- Services communicate internally via Kubernetes DNS (`<service>.<namespace>.svc.cluster.local`).
- All external traffic goes through Kong API Gateway with mTLS.

### Databases
- **PostgreSQL** — AWS RDS, Multi-AZ, automated backups (7-day retention). Version: 15.
- **Redis** — AWS ElastiCache, cluster mode disabled, 2 replicas.
- **Kafka** — AWS MSK (Managed Streaming for Kafka). 3 brokers, replication factor 3.
- **Snowflake** — external SaaS, us-west-2 region, Business Critical tier.

### Observability Stack
- **Metrics:** Datadog (`acme.datadoghq.com`) — infrastructure + APM + custom business metrics.
- **Logging:** Datadog Log Management — all services ship structured JSON logs.
- **Tracing:** Datadog APM with distributed tracing across services.
- **Alerting:** PagerDuty integrated with Datadog. Alert routing defined in `github.com/acme-corp/alerts-config`.
- **Dashboards:** Datadog dashboards for each service. Links in each repo's README.

### Security
- All inter-service calls use mTLS (Istio service mesh).
- Secrets in AWS Secrets Manager, rotated every 90 days.
- Container images scanned with Trivy in CI.
- WAF (AWS WAF v2) in front of API Gateway for DDoS and OWASP Top 10 protection.
- Penetration testing conducted quarterly by external vendor.
