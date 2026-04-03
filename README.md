# TrailMetrics: Scalable Analytics & Telemetry Platform

TrailMetrics is a cloud-native telemetry platform with a FastAPI backend, PostgreSQL + Redis pipeline, React dashboard, and Kubernetes deployment support.

## Implemented Features

- Metrics ingestion API: `POST /metrics`
- Real-time aggregation in Redis: 1m, 5m, 1h rollups
- SLO monitoring: P99 latency and error-rate budgets
- Automated alerting hooks: Slack webhook and SMTP email with severity levels and dedup cooldown
- Recovery alerting when services return to healthy state
- React dashboard with Chart.js live graphs, trends, and service drill-down
- Simulated microservices traffic generator
- Docker Compose and Minikube deployment options

## Architecture

- Backend: FastAPI + SQLAlchemy
- Database driver: pg8000 (pure Python PostgreSQL driver)
- Storage: PostgreSQL for raw telemetry, Redis for hot rollups + SLO cache
- Frontend: React + Vite + Chart.js
- Runtime: Docker containers, local Kubernetes (minikube)

## Project Layout

- `backend/`: API, data models, rollup/slo/alert services
- `backend/simulator/`: telemetry generator
- `frontend/`: dashboard UI
- `k8s/`: Kubernetes manifests
- `docs/ai-assisted-log.md`: AI generation evidence tracker

## Run Locally with Docker Compose

### Quick Start + Verify (One Command)

Run from project root:

```powershell
powershell -ExecutionPolicy Bypass -File .\\scripts\\quickstart-and-verify.ps1
```

Run with automated tests included:

```powershell
powershell -ExecutionPolicy Bypass -File .\\scripts\\quickstart-and-verify.ps1 -IncludeTests
```

The script will:

- Start all Docker services
- Wait for backend health
- Verify JWT auth + RBAC behavior
- Verify alert history endpoint
- Optionally run backend tests

1. Build and run all services:

```bash
docker compose up --build
```

2. Access services:

- Frontend: `http://localhost:5173`
- Backend API docs: `http://localhost:8000/docs`

### Local Login (JWT)

- Username: `admin`
- Password: `admin123`
- Username: `operator`
- Password: `operator123`
- Username: `viewer`
- Password: `viewer123`

Use `POST /auth/login` to obtain a bearer token. Dashboard sign-in uses this endpoint automatically.

### RBAC Permissions

- `viewer`: read-only access (`/metrics/services`, `/metrics/rollups`, `/slo/status`, `/alerts/history`, websocket stream)
- `operator`: viewer access plus control actions (`/metrics/rollups/recompute`, `/slo/evaluate`)

## Run on Minikube

1. Start minikube:

```bash
minikube start
```

2. Build images into minikube Docker daemon:

```bash
minikube image build -t trailmetrics-backend:latest ./backend
minikube image build -t trailmetrics-frontend:latest ./frontend
minikube image build -t trailmetrics-simulator:latest ./backend/simulator
```

3. Deploy manifests:

```bash
kubectl apply -f k8s/trailmetrics.yaml
```

4. Get frontend URL:

```bash
minikube service frontend -n trailmetrics --url
```

## Deploy on Render

This repository includes a Render Blueprint file (`render.yaml`) that provisions:

- `trailmetrics-postgres` (managed Postgres)
- `trailmetrics-redis` (managed Redis)
- `trailmetrics-backend` (FastAPI web service)
- `trailmetrics-frontend` (static site)

For Render workspaces that do not support worker services on the selected plan,
the backend enables an internal synthetic metrics generator via environment variables.

Steps:

1. Push this repository to GitHub.
2. In Render, select New + > Blueprint.
3. Connect this GitHub repo and select branch `main`.
4. Render detects `render.yaml`; click Apply.
5. After provisioning finishes, open the `trailmetrics-frontend` URL.

Notes:

- `JWT_SECRET_KEY` is generated automatically by Render.
- The backend reads Render Postgres URLs and auto-converts them to the `pg8000` SQLAlchemy format.
- For production, replace default auth usernames/passwords with secure values in Render environment settings.

## API Summary

### `POST /metrics`

Example payload:

```json
{
  "service_name": "checkout-service",
  "timestamp": "2026-04-02T12:00:00Z",
  "cpu_usage": 65.4,
  "latency_ms": 210.8,
  "status_code": 200
}
```

### `GET /metrics/rollups?window=1m&service_name=checkout-service`

Returns computed rollups from Redis.

### `POST /metrics/rollups/recompute`

Triggers immediate rollup computation for all services and windows.

### `GET /slo/status`

Returns SLO health and breach indicators.

### `POST /slo/evaluate`

Triggers immediate SLO evaluation and alert checks.

### `GET /alerts/history?limit=100`

Returns recent emitted alerts (breach and recovery) from Redis-backed alert history.

## AI Integration Requirement (30%+)

Use `docs/ai-assisted-log.md` to track prompts, generated modules, and approximate generated LoC by commit.

## Optional Config for Alerts

Set in backend environment:

- `SLACK_WEBHOOK_URL`
- `ALERT_MAJOR_MULTIPLIER`
- `ALERT_CRITICAL_MULTIPLIER`
- `ALERT_DEDUP_COOLDOWN_SECONDS`
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`
- `ALERT_FROM_EMAIL`, `ALERT_TO_EMAIL`

## Auth Configuration

- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`
- `JWT_ACCESS_TOKEN_EXPIRES_MINUTES`
- `AUTH_ADMIN_USERNAME`
- `AUTH_ADMIN_PASSWORD`
- `AUTH_OPERATOR_USERNAME`
- `AUTH_OPERATOR_PASSWORD`
- `AUTH_VIEWER_USERNAME`
- `AUTH_VIEWER_PASSWORD`

## Automated Tests

Focused backend tests are included for:

- JWT authentication and login
- RBAC enforcement (`viewer` vs `operator`)
- Alert dedup cooldown and alert history
- SLO severity classification

Run tests:

```bash
python -m pip install -r backend/requirements-dev.txt
python -m pytest backend/tests -q
```
