.PHONY: help up up-infra down down-v ps logs logs-all \
        migrate migrate-new migrate-down \
        test test-all test-cov lint fmt \
        shell-gateway shell-db shell-redis shell-neo4j shell-vault \
        opa-test health

# ── Help ─────────────────────────────────────────────────────

help:
	@echo ""
	@echo "  nerve.idp backend — dev commands"
	@echo ""
	@echo "  make up           spin up full stack"
	@echo "  make up-infra     spin up infra only (no app services)"
	@echo "  make down         stop all containers"
	@echo "  make down-v       stop + wipe volumes"
	@echo "  make ps           container status"
	@echo "  make health       hit /health on all 11 services"
	@echo ""
	@echo "  make logs         follow gateway logs"
	@echo "  make logs SVC=catalog  follow specific service"
	@echo "  make logs-all     follow all services"
	@echo ""
	@echo "  make migrate      run DB migrations (gateway alembic)"
	@echo "  make migrate-new msg='add foo table'"
	@echo ""
	@echo "  make test         run gateway tests"
	@echo "  make test SVC=catalog  run specific service tests"
	@echo "  make test-all     run tests across all services"
	@echo ""
	@echo "  make shell-gateway  bash into gateway"
	@echo "  make shell-db       psql into postgres"
	@echo "  make shell-redis    redis-cli"
	@echo "  make shell-neo4j    cypher-shell"
	@echo ""
	@echo "  Service URLs after 'make up':"
	@echo "    Gateway      http://localhost:8000/docs"
	@echo "    Catalog      http://localhost:8001/docs"
	@echo "    Scaffolding  http://localhost:8002/docs"
	@echo "    IaC          http://localhost:8003/docs"
	@echo "    Pipelines    http://localhost:8004/docs"
	@echo "    Observability http://localhost:8005/docs"
	@echo "    Enforcer     http://localhost:8006/docs"
	@echo "    Blast Radius http://localhost:8007/docs"
	@echo "    AI Co-pilot  http://localhost:8008/docs"
	@echo "    TechDocs     http://localhost:8009/docs"
	@echo "    Quotas       http://localhost:8010/docs"
	@echo "    Temporal UI  http://localhost:8088"
	@echo "    Grafana      http://localhost:3000  (admin/nerve_grafana)"
	@echo "    Neo4j        http://localhost:7474"
	@echo "    Prometheus   http://localhost:9090"
	@echo "    Vault        http://localhost:8200  (token: root)"
	@echo ""

# ── Stack ─────────────────────────────────────────────────────

up:
	@cp -n .env.example .env 2>/dev/null && echo "Created .env from .env.example" || true
	docker compose up -d
	@echo ""
	@echo "  nerve.idp stack is up — gateway: http://localhost:8000/docs"
	@echo ""

up-infra:
	docker compose up -d postgres pgbouncer redis neo4j vault opa temporal temporal-ui prometheus grafana

down:
	docker compose down

down-v:
	docker compose down -v

ps:
	docker compose ps

# ── Logs ──────────────────────────────────────────────────────

logs:
	docker compose logs -f $(or $(SVC),gateway)

logs-all:
	docker compose logs -f

# ── Database ──────────────────────────────────────────────────

migrate:
	docker compose exec gateway alembic upgrade head

migrate-new:
	docker compose exec gateway alembic revision --autogenerate -m "$(msg)"

migrate-down:
	docker compose exec gateway alembic downgrade -1

migrate-history:
	docker compose exec gateway alembic history

# ── Testing ───────────────────────────────────────────────────

test:
	docker compose exec $(or $(SVC),gateway) pytest tests/ -v --tb=short

test-all:
	@for svc in gateway catalog scaffolding iac pipelines observability enforcer blast ai docs quotas; do \
		echo "\n=== $$svc ==="; \
		docker compose exec $$svc pytest tests/ -v --tb=short 2>/dev/null || echo "  $$svc: skipped (not running)"; \
	done

test-cov:
	docker compose exec $(or $(SVC),gateway) pytest tests/ --cov=app --cov-report=term-missing

# ── Code quality ──────────────────────────────────────────────

lint:
	ruff check backend/
	ruff format --check backend/

fmt:
	ruff format backend/
	ruff check --fix backend/

# ── Shells ────────────────────────────────────────────────────

shell-gateway:
	docker compose exec gateway bash

shell-db:
	docker compose exec postgres psql -U nerve -d nerve

shell-redis:
	docker compose exec redis redis-cli

shell-neo4j:
	docker compose exec neo4j cypher-shell -u neo4j -p nerve_neo4j

shell-vault:
	docker compose exec vault sh

shell-%:
	docker compose exec $* bash

# ── OPA ───────────────────────────────────────────────────────

opa-test:
	opa test policies/ -v

opa-eval:
	opa eval -d policies/ -i $(input) "data.nerve.golden_path.evaluate"

# ── Health ────────────────────────────────────────────────────

health:
	@echo "Checking all services..."
	@for entry in "8000:gateway" "8001:catalog" "8002:scaffolding" "8003:iac" \
	              "8004:pipelines" "8005:observability" "8006:enforcer" "8007:blast" \
	              "8008:ai" "8009:docs" "8010:quotas"; do \
		port=$${entry%%:*}; svc=$${entry##*:}; \
		result=$$(curl -sf http://localhost:$$port/health 2>/dev/null) && \
		echo "  ✓ $$svc ($$port)" || echo "  ✗ $$svc ($$port) — not responding"; \
	done
