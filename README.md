# nerve.idp — backend

Internal Developer Platform · v2.0 · Python (FastAPI) · Kubernetes · Temporal.io · Neo4j · OPA

## Stack
- **API**: FastAPI + Uvicorn + GraphQL (Strawberry)
- **Workflows**: Temporal.io (IaC/scaffolding) + Celery (lightweight async)
- **Databases**: PostgreSQL 15 + PgBouncer · Neo4j 5 · Redis 7 · pgvector
- **Policy**: OPA + Rego + OPA Gatekeeper
- **Security**: Trivy · Semgrep · Syft · HashiCorp Vault
- **Infra**: Kubernetes · Helm 3 · ArgoCD · Prometheus · Grafana

## Quick start (local dev)
```bash
# 1. copy env file
cp .env.example .env

# 2. spin up all infrastructure
docker compose up -d

# 3. run migrations
docker compose exec gateway alembic upgrade head

# 4. hit the gateway
curl http://localhost:8000/health
```

## Monorepo structure
```
backend/          # 11 FastAPI microservices
infra/            # Helm charts, Terraform, ArgoCD manifests
policies/         # OPA Rego policy files
workflows/        # Temporal workflow definitions
docs-template/    # MkDocs golden path template
.github/          # Platform CI/CD pipelines
```

## Build phases
| Phase | Focus | Weeks |
|-------|-------|-------|
| Ph 1 | Foundation — monorepo, Docker, k8s, FastAPI skeleton | 2 |
| Ph 2 | Core platform — catalog, scaffolding, IaC, enforcer | 3 |
| Ph 3 | Differentiators — blast radius, error budgets, security | 3 |
| Ph 4 | Wow layer — AI co-pilot, fleet ops, GraphQL, TechDocs | 3 |
| Ph 5 | Production hardening — RBAC, audit log, load testing | 2 |
