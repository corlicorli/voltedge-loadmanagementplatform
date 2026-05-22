# VoltEdge — Load Management Platform

> Technical product (MVP) for the VoltEdge Mobility case — slice **A4.3 Scaling & operational
> stability**. It realises the **Load Control Context** (the *Load Management* core subdomain)
> using **Domain-Driven Design**, a real PostgreSQL-backed REST API, a React **Business
> Intelligence** dashboard, and **Grafana/Prometheus** operational monitoring — all runnable with
> a single `docker compose up`.

When a car starts charging in a load area, the area's total load rises. If it reaches the area's
capacity limit, the system **automatically reduces charging power** so the area is not overloaded.
Everything below is real: real database, real REST calls, real computed results — driven live from
a Postman collection.

---

## Table of contents

1. [What this is](#1-what-this-is)
2. [Architecture](#2-architecture)
3. [Tech stack & why](#3-tech-stack--why)
4. [Quick start — run the whole thing](#4-quick-start--run-the-whole-thing)
5. [The demo (Postman / newman)](#5-the-demo-postman--newman)
6. [Business Intelligence dashboard (§6)](#6-business-intelligence-dashboard-6)
7. [Operational monitoring (§5)](#7-operational-monitoring-5)
8. [API reference](#8-api-reference)
9. [Data model](#9-data-model)
10. [DDD → code → database mapping](#10-ddd--code--database-mapping)
11. [Testing](#11-testing)
12. [CI/CD (DevSecOps)](#12-cicd-devsecops)
13. [Operational concerns](#13-operational-concerns)
14. [Project structure](#14-project-structure)
15. [Local development (without Docker)](#15-local-development-without-docker)
16. [Configuration](#16-configuration)

---

## 1. What this is

The report documents the journey *Strategy → Domains/capabilities → Architecture → Data →
Implementation → Operation*. This repository is the **Implementation + Operation** end of that
chain for the chosen slice:

| Report section | Realised here as |
| --- | --- |
| §3 Solution design (DDD, bounded context, ubiquitous language) | `backend/app/load_control/domain` |
| §3.5 Aggregate `LoadArea`, entities, value objects | `domain/load_area.py`, `domain/entities.py`, `domain/value_objects.py` |
| §3.2 / §3.3 Domain events, commands, policies | `domain/events.py`, `application/commands.py`, `application/policies.py` |
| §3.9 API model | `backend/app/load_control/api` |
| §6 Data & analytics + Business Intelligence | `backend/app/analytics` + `frontend/` (React BI) |
| §5 Test, deployment & operation | `tests/`, `.github/workflows/ci.yml`, Grafana/Prometheus |

The MVP uses a **rule-based** load regulation model (not forecasting). A `Load Forecasting Context`
can be added later without rewriting this model — the analytics service already exposes a basic
hour-of-day forecast as that extension point.

## 2. Architecture

```mermaid
flowchart LR
  PM["Postman / newman<br/>(demo driver)"]
  BR["Browser"]
  subgraph compose["docker compose"]
    FE["React BI Dashboard<br/>:5173 — §6 BI"]
    BE["Load Control Service<br/>FastAPI · DDD<br/>:8000"]
    PG[("PostgreSQL<br/>operational + warehouse views<br/>:5432")]
    PR["Prometheus<br/>:9090"]
    GR["Grafana<br/>API monitoring + alerts<br/>:3001 — §5 Ops"]
  end
  PM -->|REST| BE
  BR --> FE
  FE -->|REST /analytics| BE
  BE -->|asyncpg| PG
  PR -->|scrape /metrics| BE
  GR -->|PromQL| PR
```

The backend follows a strict **DDD layering** (see [docs/architecture.md](docs/architecture.md)):

```
api            FastAPI routers + Pydantic schemas (the system boundary)
application    use cases, the 4 named policies, orchestration, ports (CQRS-lite)
domain         LoadArea aggregate, entities, value objects, domain events  ← no framework, no SQL
infrastructure asyncpg repository, mappers, event store, read-side queries
```

**Business Intelligence (React, §6) and operational monitoring (Grafana, §5) are deliberately
separate concerns** — Grafana watches API/service health, the React dashboard visualises
load-management business data.

## 3. Tech stack & why

| Component | Technology | Why |
| --- | --- | --- |
| API service | Python 3.12 + **FastAPI** | Async, first-class OpenAPI (`/docs`), clean layering, Pydantic validation at the boundary |
| Domain | Pure Python (frozen dataclasses) | Aggregate/entities/value objects modelled with **no framework or DB leakage** (exam §4) |
| Persistence | **PostgreSQL 16** + **asyncpg** (raw, parameterised SQL) | Real persistence; transparent domain↔DB mapping; no ORM magic; injection-safe |
| BI dashboard | **React + TypeScript + Vite + Recharts** | Independent analytics UI for load-management business data (§6) |
| Ops monitoring | **Prometheus + Grafana** (provisioned as code) | Standardised metrics + alarms for the API (§5, the A4.3 pain point) |
| Orchestration | **Docker Compose** | One-command, reproducible run of the entire solution |
| CI/CD | **GitHub Actions** | Lint, tests-with-DB, frontend build, image build (DevSecOps) |
| Demo | **Postman + newman** | Real REST calls reproducing the report scenario |

## 4. Quick start — run the whole thing

**Prerequisite:** Docker Desktop (Docker Engine + Compose).

```bash
git clone https://github.com/corlicorli/voltedge-loadmanagementplatform.git
cd voltedge-loadmanagementplatform
cp .env.example .env        # optional — defaults work out of the box
docker compose up --build   # add -d to run detached
```

On startup the backend automatically applies the SQL migrations and seeds **LoadArea YN**
(24 chargers, 240 kW max, ~233 kW baseline + 7 days of historical samples for the BI charts).

| Service | URL | Notes |
| --- | --- | --- |
| React BI dashboard | http://localhost:5173 | §6 Business Intelligence |
| API + Swagger UI | http://localhost:8000/docs | Load Control + Analytics |
| API health | http://localhost:8000/health | liveness + DB readiness |
| API metrics | http://localhost:8000/metrics | Prometheus exposition |
| Grafana | http://localhost:3001 | §5 ops monitoring · login `admin` / `admin` |
| Prometheus | http://localhost:9090 | targets + alert rules |
| PostgreSQL | localhost:5432 | `voltedge` / `voltedge` |

> **Port note:** Grafana is on **3001** (host port 3000 is often used by other dev tools). Change
> it with `GRAFANA_PORT` in `.env`.

Stop and reset to a clean database:

```bash
docker compose down -v   # -v wipes the DB volume so the next 'up' re-seeds
```

## 5. The demo (Postman / newman)

The collection reproduces the report's scenario for LoadArea YN:

> baseline **233 kW** (WARNING) → a new 11 kW session → **244 kW** (CRITICAL, −4 kW over)
> → automatic **10% regulation** → **219.6 kW** (stabilised).

**Option A — Postman GUI:** import `postman/VoltEdge-LoadManagement.postman_collection.json` and
`postman/VoltEdge-Local.postman_environment.json`, select the *VoltEdge Local* environment, and run
the collection top to bottom (each request has test assertions).

**Option B — CLI (newman):**

```bash
./postman/run-demo.sh
```

For the canonical "244 → 219.6" narrative, run it against a freshly started stack
(`docker compose down -v && docker compose up`).

## 6. Business Intelligence dashboard (§6)

Open **http://localhost:5173**. The dashboard polls the analytics API every 5 s and shows:

- **KPIs**: current load gauge + status, available capacity, active sessions, 24 h peak, open interventions
- **Load trend** (24 h) with warning/critical threshold lines
- **Predictive forecast** (next 12 h, hour-of-day model)
- **Daily peak load** (7 days) coloured by status
- **Status distribution** (time spent STABLE / WARNING / CRITICAL)
- **Regulation events** timeline (diagnostic) + active sessions + load adjustments

Run the Postman demo while it's open to watch values update live.

## 7. Operational monitoring (§5)

Open **http://localhost:3001** (`admin` / `admin`) → dashboard **"VoltEdge — Load Control API
Monitoring"**. It is provisioned as code from `ops/grafana/` and shows API request rate, error rate,
p50/p95/p99 latency, status, and request mix — sourced from Prometheus scraping the backend
`/metrics`. Prometheus alert rules (`ops/prometheus/alerts.yml`) cover **API down**, **high 5xx rate**
and **high p95 latency** (see http://localhost:9090/alerts).

This layer is intentionally independent of the BI dashboard.

## 8. API reference

**Load Control** (`/load-areas/{areaCode}`)

| Method | Path | Description |
| --- | --- | --- |
| POST | `/sessions` | Start a charging session (triggers regulation if needed) |
| GET | `/status` | Current `LoadStatus`, load, available capacity |
| GET | `/sessions` | Active charging sessions |
| GET | `/adjustments` | Load adjustments made by regulation |
| POST | `/evaluate` | Re-evaluate load and regulate if needed |

**Analytics / BI** (`/analytics/{areaCode}`): `kpis`, `load-timeseries`, `hourly-utilisation`,
`daily-peaks`, `status-distribution`, `regulation-events`, `forecast`.

Example:

```bash
curl -X POST localhost:8000/load-areas/YN/sessions \
  -H 'Content-Type: application/json' -d '{"chargerId":"YN-23","powerLevelKw":11}'
```

Field names match the report's ubiquitous language as camelCase (`currentLoadKw`, `maxCapacityKw`,
`availableCapacityKw`, `status`, `activeSessionCount`). Full interactive docs at `/docs`.

## 9. Data model

Operational tables: `load_areas` (aggregate root), `chargers`, `charging_sessions`, `load_rules`,
`load_adjustments`, `intervention_requests`, plus `domain_events` (event store) and `load_samples`
(time-series projection). Read-model + warehouse **views** (`v_load_area_status`, `v_active_sessions`,
`v_charger_power`, `v_load_adjustments`, `v_load_utilisation_hourly`, `v_peak_loads_daily`,
`v_regulation_events`, `v_area_kpis`, …) form the BI/analytics layer. See
[`backend/migrations/`](backend/migrations).

## 10. DDD → code → database mapping

The explicit coupling required by exam §4 is documented in
**[docs/ddd-mapping.md](docs/ddd-mapping.md)** — a table from each design concept (aggregate,
entities, value objects, the 9 events, the 4 policies) to the exact file and database table/column.

## 11. Testing

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest --cov=app --cov-report=term-missing      # 33 tests, ~92% coverage
```

- **Unit tests** (`tests/unit`) cover the domain rules and the full regulation cascade — no DB needed.
- **API/integration tests** (`tests/api`) run through HTTP against PostgreSQL; they auto-skip if no
  database is reachable at `DATABASE_URL`.

## 12. CI/CD (DevSecOps)

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs on every push/PR:

1. **backend** — `ruff` lint + `pytest` (with a PostgreSQL service container) + coverage
2. **frontend** — `npm ci` + `tsc` type-check + `vite build`
3. **docker** — `docker compose build` (validates every image)

## 13. Operational concerns

- **Logging:** structured JSON to stdout (`app/platform/logging_config.py`) — standardised for aggregation.
- **Monitoring/alarms:** Prometheus + Grafana (§7).
- **Health:** `/health` checks DB connectivity (used by the compose healthcheck).
- **Error handling:** global handlers map `LoadAreaNotFound` → 404 and domain validation → 422.
- **Rollback:** stateless services roll back by redeploying a previous image; migrations are
  idempotent and tracked in `schema_migrations`; `docker compose down -v` resets state.

## 14. Project structure

```
backend/      FastAPI service (DDD layers), migrations, seeds, tests, Dockerfile
  app/load_control/{domain,application,infrastructure,api}
  app/analytics/{application,api}
  app/platform/{config,database,logging_config,dependencies}
frontend/     React + TS BI dashboard (Vite, Recharts, nginx Dockerfile)
ops/          prometheus/ (scrape + alerts) and grafana/ (datasource, dashboard, provisioning)
postman/      collection + environment + newman runner
docs/         architecture.md, ddd-mapping.md
docker-compose.yml, .github/workflows/ci.yml
```

## 15. Local development (without Docker)

```bash
# Postgres (any local instance), then:
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
DATABASE_URL=postgresql://voltedge:voltedge@localhost:5432/voltedge \
  uvicorn app.main:app --reload --port 8000

cd frontend && npm install && npm run dev   # http://localhost:5173
```

## 16. Configuration

All settings come from environment variables (see [`.env.example`](.env.example)): `DATABASE_URL`,
`APP_ENV`, `LOG_LEVEL`, `RUN_MIGRATIONS_ON_STARTUP`, `SEED_ON_STARTUP`, `VITE_API_BASE_URL`,
`GRAFANA_PORT`, and the Postgres/Grafana credentials. No secrets are committed.
