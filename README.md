# VoltEdge — Load Management Platform

> Teknisk produkt (MVP) til VoltEdge Mobility-casen — slice **A4.3 Skalering og driftsstabilitet**.
> Det realiserer **Load Control Context** (core-subdomænet *Load Management*) med
> **Domain-Driven Design**, et reelt PostgreSQL-baseret REST-API, et React-baseret
> **Business Intelligence**-dashboard og **Grafana/Prometheus**-driftsovervågning — det hele kørbart
> med en enkelt `docker compose up`.

Når en bil starter opladning i et load area, stiger områdets samlede belastning. Hvis belastningen
når områdets kapacitetsgrænse, **reducerer systemet automatisk ladeeffekten**, så området ikke
overbelastes. Alt herunder er reelt: rigtig database, rigtige REST-kald og rigtige beregnede
resultater — drevet live fra en Postman-collection.

---

## Indholdsfortegnelse

1. [Hvad er dette](#1-hvad-er-dette)
2. [Arkitektur](#2-arkitektur)
3. [Teknologivalg](#3-teknologivalg)
4. [Hurtig start](#4-hurtig-start)
5. [Demo med Postman](#5-demo-med-postman)
6. [Business Intelligence-dashboard (§6)](#6-business-intelligence-dashboard-6)
7. [Driftsovervågning (§5)](#7-driftsovervågning-5)
8. [API-reference](#8-api-reference)
9. [Datamodel](#9-datamodel)
10. [DDD-til-kode-til-database-mapping](#10-ddd-til-kode-til-database-mapping)
11. [Test](#11-test)
12. [CI/CD (DevSecOps)](#12-cicd-devsecops)
13. [Driftshensyn](#13-driftshensyn)
14. [Projektstruktur](#14-projektstruktur)
15. [Lokal udvikling (uden Docker)](#15-lokal-udvikling-uden-docker)
16. [Konfiguration](#16-konfiguration)

---

## 1. Hvad er dette

Rapporten dokumenterer rejsen *Strategi → Domæner/kapabiliteter → Arkitektur → Data →
Implementering → Drift*. Dette repository udgør **implementerings- og driftsdelen** af den kæde for
den valgte slice:

| Rapportafsnit | Realiseret her som |
| --- | --- |
| §3 Løsningsdesign (DDD, bounded context, ubiquitous language) | `backend/app/load_control/domain` |
| §3.5 Aggregat `LoadArea`, entiteter, value objects | `domain/load_area.py`, `domain/entities.py`, `domain/value_objects.py` |
| §3.2 / §3.3 Domain events, commands, policies | `domain/events.py`, `application/commands.py`, `application/policies.py` |
| §3.9 API-model | `backend/app/load_control/api` |
| §6 Data & analyse + Business Intelligence | `backend/app/analytics` + `frontend/` (React BI) |
| §5 Test, deployment & drift | `tests/`, `.github/workflows/ci.yml`, Grafana/Prometheus |

MVP'en anvender en **regelbaseret** load regulation-model (ikke forecasting), i tråd med rapporten.
Et `Load Forecasting Context` kan tilføjes senere som et separat bounded context uden at omskrive
denne model.

## 2. Arkitektur

```mermaid
flowchart LR
  PM["Postman / newman<br/>(demo)"]
  BR["Browser"]
  subgraph compose["docker compose"]
    FE["React BI-dashboard<br/>:5173 — §6 BI"]
    BE["Load Control Service<br/>FastAPI · DDD<br/>:8000"]
    PG[("PostgreSQL<br/>operationel + warehouse-views<br/>:5432")]
    PR["Prometheus<br/>:9090"]
    GR["Grafana<br/>API-overvågning + alarmer<br/>:3001 — §5 drift"]
  end
  PM -->|REST| BE
  BR --> FE
  FE -->|REST /analytics| BE
  BE -->|asyncpg| PG
  PR -->|scrape /metrics| BE
  GR -->|PromQL| PR
```

Backend følger en stringent **DDD-lagdeling** (se [docs/architecture.md](docs/architecture.md)):

```
api            FastAPI-routers + Pydantic-skemaer (systemgrænsen)
application    use cases, de 4 navngivne policies, orkestrering, ports (CQRS-lite)
domain         LoadArea-aggregat, entiteter, value objects, domain events  ← ingen framework, ingen SQL
infrastructure asyncpg-repository, mappers, event store, læse-queries
```

**Business Intelligence (React, §6) og driftsovervågning (Grafana, §5) er bevidst adskilte
ansvarsområder** — Grafana overvåger API'ets/servicens sundhed, mens React-dashboardet visualiserer
load management-forretningsdata.

## 3. Teknologivalg

| Komponent | Teknologi | Begrundelse |
| --- | --- | --- |
| API-service | Python 3.12 + **FastAPI** | Asynkron, indbygget OpenAPI (`/docs`), ren lagdeling, Pydantic-validering ved grænsen |
| Domæne | Ren Python (frozen dataclasses) | Aggregat/entiteter/value objects modelleret **uden framework- eller DB-afsmitning** (eksamen §4) |
| Persistering | **PostgreSQL 16** + **asyncpg** (rå, parametriseret SQL) | Reel persistering; transparent domæne↔DB-mapping; ingen ORM-magi; sikret mod injection |
| BI-dashboard | **React + TypeScript + Vite + Recharts + shadcn/ui** | Selvstændig analyse-UI til load management-forretningsdata (§6) |
| Driftsovervågning | **Prometheus + Grafana** (provisioneret som kode) | Standardiserede metrics + alarmer for API'et (§5, A4.3-smertepunktet) |
| Orkestrering | **Docker Compose** | Reproducerbar kørsel af hele løsningen med én kommando |
| CI/CD | **GitHub Actions** | Lint, test-med-DB, frontend-build, image-build (DevSecOps) |
| Demo | **Postman + newman** | Rigtige REST-kald, der gengiver rapportens scenarie |

## 4. Hurtig start

**Forudsætning:** Docker Desktop (Docker Engine + Compose).

```bash
git clone https://github.com/corlicorli/voltedge-loadmanagementplatform.git
cd voltedge-loadmanagementplatform
cp .env.example .env        # valgfrit — standardværdierne virker som de er
docker compose up --build   # tilføj -d for at køre i baggrunden
```

Ved opstart kører backenden automatisk SQL-migreringerne og seeder **LoadArea YN**
(24 ladestandere, 240 kW max, ~233 kW baseline + 7 dages historiske samples til BI-graferne).

| Service | URL | Bemærkninger |
| --- | --- | --- |
| React BI-dashboard | http://localhost:5173 | §6 Business Intelligence |
| API + Swagger UI | http://localhost:8000/docs | Load Control + Analytics |
| API health | http://localhost:8000/health | liveness + DB-readiness |
| API metrics | http://localhost:8000/metrics | Prometheus-eksponering |
| Grafana | http://localhost:3001 | §5 driftsovervågning · login `admin` / `admin` |
| Prometheus | http://localhost:9090 | targets + alert rules |
| PostgreSQL | localhost:5432 | `voltedge` / `voltedge` |

> **Bemærkning om port:** Grafana kører på **3001** (host-port 3000 bruges ofte af andre
> udviklingsværktøjer). Skift den med `GRAFANA_PORT` i `.env`.

Stop og nulstil til en ren database:

```bash
docker compose down -v   # -v sletter DB-volumen, så næste 'up' seeder forfra
```

## 5. Demo med Postman

Collectionen gengiver rapportens scenarie for LoadArea YN:

> baseline **233 kW** (WARNING) → en ny 11 kW-session → **244 kW** (CRITICAL, −4 kW over)
> → automatisk **10 % regulering** → **219,6 kW** (stabiliseret).

**Mulighed A — Postman GUI:** importér `postman/VoltEdge-LoadManagement.postman_collection.json` og
`postman/VoltEdge-Local.postman_environment.json`, vælg miljøet *VoltEdge Local*, og kør collectionen
fra top til bund (hver request har test-assertions).

**Mulighed B — CLI (newman):**

```bash
./postman/run-demo.sh
```

For det kanoniske "244 → 219,6"-forløb skal det køres mod en netop startet stack
(`docker compose down -v && docker compose up`).

## 6. Business Intelligence-dashboard (§6)

Åbn **http://localhost:5173**. Dashboardet (shadcn/ui — hvid baggrund med mørke komponenter) poller
analyse-API'et hvert 5. sekund og viser:

- **KPI'er**: gauge for aktuel belastning + status, ledig kapacitet, aktive sessioner, 24-timers peak, åbne interventioner
- **Belastningsudvikling** (24 t) med warning/critical-grænselinjer
- **Daglig peak-belastning** (7 dage) farvet efter status
- **Statusfordeling** (tid brugt i STABLE / WARNING / CRITICAL)
- **Regulerings-events** tidslinje (diagnostisk) + aktive sessioner + load adjustments

Kør Postman-demoen mens dashboardet er åbent for at se værdierne opdatere live.

## 7. Driftsovervågning (§5)

Åbn **http://localhost:3001** (`admin` / `admin`) → dashboardet **"VoltEdge — Load Control API
Monitoring"**. Det er provisioneret som kode fra `ops/grafana/` og viser API'ets request rate,
fejlrate, p50/p95/p99-latency, status og request-fordeling — baseret på at Prometheus scraper
backendens `/metrics`. Prometheus alert rules (`ops/prometheus/alerts.yml`) dækker **API nede**,
**høj 5xx-rate** og **høj p95-latency** (se http://localhost:9090/alerts).

Dette lag er bevidst uafhængigt af BI-dashboardet.

## 8. API-reference

**Load Control** (`/load-areas/{areaCode}`)

| Metode | Sti | Beskrivelse |
| --- | --- | --- |
| POST | `/sessions` | Start en charging session (udløser regulering hvis nødvendigt) |
| GET | `/status` | Aktuel `LoadStatus`, belastning, ledig kapacitet |
| GET | `/sessions` | Aktive charging sessions |
| GET | `/adjustments` | Load adjustments foretaget af reguleringen |
| POST | `/evaluate` | Genvurder belastning og regulér hvis nødvendigt |

**Analytics / BI** (`/analytics/{areaCode}`): `kpis`, `load-timeseries`, `hourly-utilisation`,
`daily-peaks`, `status-distribution`, `regulation-events`.

Eksempel:

```bash
curl -X POST localhost:8000/load-areas/YN/sessions \
  -H 'Content-Type: application/json' -d '{"chargerId":"YN-23","powerLevelKw":11}'
```

Feltnavne følger rapportens ubiquitous language i camelCase (`currentLoadKw`, `maxCapacityKw`,
`availableCapacityKw`, `status`, `activeSessionCount`). Fuld interaktiv dokumentation på `/docs`.

## 9. Datamodel

Operationelle tabeller: `load_areas` (aggregate root), `chargers`, `charging_sessions`, `load_rules`,
`load_adjustments`, `intervention_requests`, samt `domain_events` (event store) og `load_samples`
(tidsserie-projektion). Læsemodel- + warehouse-**views** (`v_load_area_status`, `v_active_sessions`,
`v_charger_power`, `v_load_adjustments`, `v_load_utilisation_hourly`, `v_peak_loads_daily`,
`v_regulation_events`, `v_area_kpis`, …) udgør BI-/analyselaget. Se
[`backend/migrations/`](backend/migrations).

## 10. DDD-til-kode-til-database-mapping

Den eksplicitte kobling, som eksamen §4 kræver, er dokumenteret i
**[docs/ddd-mapping.md](docs/ddd-mapping.md)** — en tabel fra hvert designbegreb (aggregat,
entiteter, value objects, de 9 events, de 4 policies) til den præcise fil og databasetabel/-kolonne.

## 11. Test

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest --cov=app --cov-report=term-missing      # 32 tests, ~92 % dækning
```

- **Unit-tests** (`tests/unit`) dækker domæne-reglerne og hele reguleringskaskaden — kræver ingen DB.
- **API-/integrationstests** (`tests/api`) kører via HTTP mod PostgreSQL; de springes automatisk over,
  hvis ingen database er tilgængelig på `DATABASE_URL`.

## 12. CI/CD (DevSecOps)

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) kører ved hvert push/PR:

1. **backend** — `ruff`-lint + `pytest` (med en PostgreSQL-service-container) + dækning
2. **frontend** — `npm ci` + `tsc`-typecheck + `vite build`
3. **docker** — `docker compose build` (validerer hvert image)

## 13. Driftshensyn

- **Logning:** struktureret JSON til stdout (`app/platform/logging_config.py`) — standardiseret til aggregering.
- **Overvågning/alarmer:** Prometheus + Grafana (§7).
- **Health:** `/health` tjekker DB-forbindelsen (bruges af compose-healthchecket).
- **Fejlhåndtering:** globale handlers mapper `LoadAreaNotFound` → 404 og domæne-validering → 422.
- **Rollback:** stateless services rulles tilbage ved at gen-deploye et tidligere image; migreringer er
  idempotente og spores i `schema_migrations`; `docker compose down -v` nulstiller tilstanden.

## 14. Projektstruktur

```
backend/      FastAPI-service (DDD-lag), migreringer, seeds, tests, Dockerfile
  app/load_control/{domain,application,infrastructure,api}
  app/analytics/{application,api}
  app/platform/{config,database,logging_config,dependencies}
frontend/     React + TS BI-dashboard (Vite, shadcn/ui, Recharts, nginx Dockerfile)
ops/          prometheus/ (scrape + alarmer) og grafana/ (datasource, dashboard, provisionering)
postman/      collection + miljø + newman-runner
docs/         architecture.md, ddd-mapping.md
docker-compose.yml, .github/workflows/ci.yml
```

## 15. Lokal udvikling (uden Docker)

```bash
# Postgres (en hvilken som helst lokal instans), derefter:
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
DATABASE_URL=postgresql://voltedge:voltedge@localhost:5432/voltedge \
  uvicorn app.main:app --reload --port 8000

cd frontend && npm install && npm run dev   # http://localhost:5173
```

## 16. Konfiguration

Alle indstillinger kommer fra miljøvariabler (se [`.env.example`](.env.example)): `DATABASE_URL`,
`APP_ENV`, `LOG_LEVEL`, `RUN_MIGRATIONS_ON_STARTUP`, `SEED_ON_STARTUP`, `VITE_API_BASE_URL`,
`GRAFANA_PORT` samt Postgres-/Grafana-loginoplysninger. Ingen hemmeligheder er committet.
