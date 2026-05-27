# VoltEdge — Load Management Platform

Load management-platform til **VoltEdge Mobility A/S** (KEA 6. semester — Teknisk produkt, slice **A4.3 Skalering og driftsstabilitet**). Realiserer **Load Control Context** (core-subdomænet *Load Management*) med Domain-Driven Design.

Når en bil starter opladning i et load area, stiger den samlede belastning. Når belastningen rammer områdets kapacitetsgrænse, **reducerer systemet automatisk ladeeffekten**, så området ikke overbelastes — alt sammen reelt: rigtig database, rigtige REST-kald og rigtige beregnede resultater.

**Stack:** FastAPI · MongoDB · Motor · React · Recharts · Docker · Prometheus · Grafana · GitHub Actions CI

[![CI](https://github.com/corlicorli/voltedge-loadmanagementplatform/actions/workflows/ci.yml/badge.svg)](https://github.com/corlicorli/voltedge-loadmanagementplatform/actions/workflows/ci.yml)

## Domæne — automatisk load regulation (event → beslutning → handling)

```
Hændelse    POST /load-areas/YN/sessions (ny 11 kW-session)   ─► charging_sessions
            ChargingSessionStarted · LoadAreaUpdated             (skrivemodel)

Beslutning  belastning når 240 kW (100%)  →  CRITICAL          ─► domain_events
            LoadRegulationPolicy + PowerReductionPolicy           (event store / audit)

Handling    reducér ladeeffekt 10%                             ─► load_adjustments
            242 kW → 217,8 kW → LoadAreaStabilized             ─► load_samples (BI-tidsserie)
```

Modellen er **regelbaseret** (ikke forecasting), i tråd med rapporten. **BI (React, §6) og driftsovervågning (Grafana, §5) er bevidst adskilte** — Grafana overvåger API'ets sundhed, React visualiserer load management-forretningsdata.

## Arkitektur

```
┌──────────────┐   REST /load-areas, /analytics    ┌────────────────────┐
│ Postman /    │ ────────────────────────────────► │  FastAPI            │
│ newman       │ ◄──────────────────────────────── │  Load Control       │
└──────────────┘        JSON (camelCase)           │  Service  :8000     │
┌──────────────┐   REST /analytics (poll 5 s)      │  DDD-lag:           │
│ React BI      │ ───────────────────────────────► │  api·app·domain·inf │
│ dashboard     │ ◄─────────────────────────────── │                     │
│ :5173 (§6)    │                                  └──────────┬──────────┘
└──────────────┘                                              │ motor (async)
                                                              ▼
                                                   ┌────────────────────┐
                                                   │ MongoDB  :27017     │
                                                   │ lokalt ELLER Atlas  │
                                                   │ 8 collections       │
                                                   └────────────────────┘
                                                              ▲ scrape /metrics
┌──────────────┐     PromQL       ┌────────────────┐         │
│ Grafana       │ ◄────────────── │ Prometheus     │ ────────┘
│ :3001 (§5)    │                 │ :9090          │
└──────────────┘                 └────────────────┘
```

DDD-lagdeling: `api` (FastAPI + Pydantic, systemgrænse) → `application` (use cases, de 4 policies, ports, CQRS) → `domain` (LoadArea-aggregat, entiteter, value objects, events — ingen framework, ingen DB) → `infrastructure` (Motor-repository, mappers, event store, læse-aggregeringer).

## Krav

- **Docker Desktop** (anbefalet) — eller **Python 3.12+** + **Node 20+** + en kørende MongoDB

## Quick start (Docker)

Hele stacken (MongoDB + mongo-express + backend + React BI + Prometheus + Grafana) starter med én kommando:

```bash
git clone https://github.com/corlicorli/voltedge-loadmanagementplatform.git
cd voltedge-loadmanagementplatform
docker compose up --build -d
```

Systemet starter **tomt** — ingen pre-seedet/simuleret data. Du bygger YN op via API'et: kør Postman-mappen *Onboarding* (registrerer området + dens 24 ladestandere + baseline-lasten — alt via rigtige API-kald), eller hele demoen på CLI med `./postman/run-demo.sh`.

| Service | URL | Til hvad |
|---|---|---|
| **React BI-dashboard** | http://localhost:5173 | §6 Business Intelligence (load management-data) |
| **API + Swagger UI** | http://localhost:8000/docs | Test endpoints interaktivt |
| **Grafana** | http://localhost:3001 | §5 API-/driftsovervågning · login `admin`/`admin` |
| Prometheus | http://localhost:9090 | Rå metric-queries + alert rules |
| mongo-express | http://localhost:8081 | Browse MongoDB |
| MongoDB | `localhost:27017` | mongosh-adgang |

> Grafana kører på **3001** (host-port 3000 bruges ofte af andre dev-værktøjer). Skift med `GRAFANA_PORT`.

**Kør mod MongoDB Atlas (cloud)** i stedet for den lokale container: sæt `MONGO_URL=mongodb+srv://…` i `.env`. Resten er uændret — samme image lokalt og i skyen. Nulstil lokalt med `docker compose down -v`.

## Demo — fra tom database til regulering

Systemet starter **tomt**; hele forløbet (rapportens scenarie) bygges op via API'et — intet simuleres.

**1. Onboarding** (Postman-mappen *Onboarding*) — kunden registrerer sit load area YN, dens **24 ladestandere** og baseline-opladningerne (→ **231 kW**, WARNING) — alt via rigtige API-kald, intet script:

```bash
curl -X POST http://localhost:8000/load-areas \
  -H 'content-type: application/json' \
  -d '{"areaCode":"YN","areaName":"Ydre Nørrebro","maxCapacityKw":240}'
# + POST /load-areas/YN/chargers (YN-01..YN-24) og /sessions (baseline) — Onboarding-mappen gør det automatisk
```

**2. Regulering** (Postman-mappen *Regulering*) — en ledig lader (YN-22) tages i brug → **242 kW (CRITICAL)** → **10% regulering** → **217,8 kW**:

```bash
curl -X POST http://localhost:8000/load-areas/YN/sessions \
  -H 'content-type: application/json' -d '{"chargerId":"YN-22","powerLevelKw":11}'
curl http://localhost:8000/analytics/YN/regulation-events    # nu fyldt
```

Eller kør hele forløbet automatisk: `./postman/run-demo.sh` (onboarding → regulering → analytics).

**Postman / newman:** collectionen har mapperne **Setup · Onboarding · Regulering · Analytics** ([`postman/VoltEdge-LoadManagement.postman_collection.json`](postman/VoltEdge-LoadManagement.postman_collection.json)). YN har **24 faste standere** — onboarding-mappen registrerer netop dem, ingen ud over de 24. `run-demo.sh` kører hele collectionen end-to-end:

```bash
./postman/run-demo.sh
```

Åbn BI-dashboardet mens du kører demoen for at se værdierne opdatere live (poll hvert 5. sekund, dansk 24-timers tidsformat).

## Test

```bash
cd backend && pip install -r requirements-dev.txt
pytest --cov=app --cov-report=term-missing
```

Forventet: `38 passed`. Unit-tests dækker domæne + hele reguleringskaskaden (ingen DB). Integration-tests bygger YN op via API'et og kører mod MongoDB; de **skipper pænt**, hvis ingen DB er på `MONGO_URL`. CI kører automatisk ved push til `main` ([Actions](https://github.com/corlicorli/voltedge-loadmanagementplatform/actions)).

## Endpoints

### Onboarding (`/load-areas`)
| Endpoint | Metode | Beskrivelse |
|---|---|---|
| `/load-areas` | POST | Registrér et nyt load area (opretter reguleringsreglerne) |
| `/load-areas` | GET | List alle registrerede områder |

### Load Control (`/load-areas/{areaCode}`)
| Endpoint | Metode | Beskrivelse |
|---|---|---|
| `/sessions` | POST | Start charging session (udløser regulering hvis nødvendigt) |
| `/status` | GET | Aktuel `LoadStatus`, belastning, ledig kapacitet |
| `/sessions` | GET | Aktive charging sessions |
| `/adjustments` | GET | Load adjustments foretaget af reguleringen |
| `/evaluate` | POST | Genvurder belastning og regulér |
| `/chargers` | POST / GET | Registrér / list ladestandere (navn, occupancy, online/offline, output) |
| `/chargers/{id}` | GET | Én laders detalje: navn, occupancy, online/offline, aktuel kW-output |
| `/chargers/{id}/heartbeat` | POST | Laderens heartbeat → markerer den ONLINE |

### Analytics / BI (`/analytics/{areaCode}`)
| Endpoint | Metode | Beskrivelse |
|---|---|---|
| `/kpis` | GET | Headline-KPI'er (deskriptiv) |
| `/load-timeseries` | GET | Belastningsudvikling over tid |
| `/hourly-utilisation` · `/daily-peaks` | GET | Time-/dags-aggregering |
| `/status-distribution` | GET | Tid brugt i STABLE/WARNING/CRITICAL |
| `/regulation-events` · `/event-counts` | GET | Diagnostisk: hvorfor regulering skete |

### Drift
| Endpoint | Metode | Beskrivelse |
|---|---|---|
| `/health` | GET | Liveness + DB-readiness (pinger Mongo) |
| `/metrics` | GET | Prometheus-format API-metrics |
| `/docs` | GET | Auto-genereret Swagger UI |

## Datamodel — 8 MongoDB collections

`_id` = den naturlige nøgle (area code / charger id / uuid). Skrivemodellen; læsemodellen (CQRS) er aggregeringspipelines. **Alle collections starter tomme** og fyldes via API'et (Postman *Onboarding*-mappen) — intet seedes.

| Collection | Indhold | Kategori |
|---|---|---|
| `load_areas` | Load area (aggregate root) | Domain aggregate |
| `chargers` | Ladestandere | Domain entity |
| `charging_sessions` | Opladningssessioner | Domain entity |
| `load_rules` | Regulerings-regler | Domain entity |
| `load_adjustments` | Effekt-reduktioner | **Regulerings-log** |
| `intervention_requests` | Manuelle interventioner | **Audit-log** |
| `domain_events` | Alle 9 domain events | **Event store (audit)** |
| `load_samples` | Belastnings-tidsserie | **BI-projektion** |

Indekser oprettes idempotent ved opstart (`backend/app/platform/database.py`).

## Konfiguration (env-vars)

| Variabel | Default | Beskrivelse |
|---|---|---|
| `MONGO_URL` | `mongodb://mongo:27017` | Connection-string (sæt til `mongodb+srv://…` for Atlas) |
| `MONGO_DB` | `voltedge` | Database-navn |
| `APP_ENV` · `LOG_LEVEL` | `development` · `INFO` | Miljø + logniveau |
| `VITE_API_BASE_URL` | `http://localhost:8000` | API-base for React-build |
| `GRAFANA_PORT` | `3001` | Host-port for Grafana |

Alt kommer fra miljøvariabler (skabelon: [`.env.example`](.env.example)). `.env` er git-ignoreret — **ingen hemmeligheder committes** (Atlas-strengen sættes lokalt).

## Projektstruktur

```
backend/
  app/load_control/{domain,application,infrastructure,api}   — DDD-lag for Load Control Context
  app/analytics/{application,api}                            — dataanalyse-domæneservice (§6)
  app/platform/{config,database,logging_config,dependencies} — Motor-klient, config, JSON-logning
  tests/                — pytest (38: unit + integration)
  Dockerfile
frontend/               — React + TS BI-dashboard (Vite, shadcn/ui, Recharts, nginx)
ops/prometheus/         — scrape-konfig + alert rules
ops/grafana/            — datasource, dashboard, provisionering (as code)
postman/                — collection + miljø + newman-runner
docker-compose.yml      — hele stacken · .github/workflows/ci.yml — CI
```

## Mapping til opgavekrav (§2.2)

| Krav | Implementering |
|---|---|
| Fungerende API | FastAPI Load Control + Analytics, interaktiv Swagger på `/docs` |
| Cloud-tjeneste | **MongoDB Atlas** (managed) — samme image lokalt og i skyen |
| Container-orkestrering | **Docker Compose** — hele stacken med én kommando |
| Dataanalyse som domæneservice | `AnalyticsService` — deskriptiv + diagnostisk via aggregeringspipelines |
| BI-dashboards | Selvstændigt **React-dashboard** (§6), adskilt fra ops-overvågning |
| Logning / monitorering / alarmer | JSON-logs + Prometheus + Grafana + alert rules (§5) |
| Fejlhåndtering / rollback | Globale handlers (404/422); stateless services, idempotente indexer, `down -v` nulstiller |
| CI/CD | GitHub Actions: `ruff` + `pytest` (mongo-service) + `docker compose build` |
| DDD → kode → database (§4) | Dokumenteret i rapporten; afspejlet 1:1 i `app/load_control/domain` + MongoDB-collections |
