# dispatch-map

Monorepo containing a FastAPI backend (`packages/api`), React frontend (`packages/web`), background scraper (`packages/dispatch-consumer`), shared database models (`packages/db`), and database migrations (`packages/migrations`).

---

## Quick Start with Docker Compose

The easiest way to run the entire stack is with Docker Compose.

### 1. Environment Setup

Copy the example environment file:

```bash
cp .env.example .env
```

Review `.env` to customize database credentials or ports if desired.

### 2. Local Development (with live-reload & HMR)

Start all services (PostgreSQL, automatic migrations, FastAPI dev server, Vite dev server, and consumer worker):

```bash
# Using the helper script:
./run-dev.sh docker

# Or directly with Docker Compose:
docker compose up --build
```

- **Web Frontend**: `http://localhost:5173` (Vite dev server with Hot Module Replacement, proxying API requests to FastAPI)
- **API & Docs**: `http://localhost:8000/docs` (FastAPI Swagger UI)
- **Database**: `localhost:5430` (`postgresql://dispatch:dispatch@localhost:5430/dispatch_map`)

Code changes in `packages/web`, `packages/api`, `packages/db`, and `packages/dispatch-consumer` reload automatically inside the containers.

### 3. Production Deployment (Single-Port Unified Service)

In production, `packages/web` is compiled directly into FastAPI's static assets directory. FastAPI serves both the React Single Page Application (SPA) and REST/SSE endpoints from port `8000`:

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

- Access the unified application at `http://localhost:8000`.
- No separate frontend container or reverse proxy is required.

---

## Standalone Package Docker Builds

Each service can also be built as a standalone container image from the repository root:

```bash
# FastAPI Backend (Production target - includes built React frontend):
docker build -f packages/api/Dockerfile --target production -t dispatch-map-api:prod .

# FastAPI Backend (Development target):
docker build -f packages/api/Dockerfile --target development -t dispatch-map-api:dev .

# Dispatch Consumer Worker:
docker build -f packages/dispatch-consumer/Dockerfile -t dispatch-map-consumer:latest .

# Database Migrations Runner:
docker build -f packages/migrations/Dockerfile -t dispatch-map-migrations:latest .

# Web Frontend (Vite Dev Server):
docker build -f packages/web/Dockerfile -t dispatch-map-web:dev packages/web
```

---

## Local Development (Without Docker)

You can also run services individually on your host machine.

### Prerequisites

- [uv](https://docs.astral.sh/uv/) for Python package management
- Node.js 20+ and npm
- A running PostgreSQL instance (e.g. `docker build -t dispatch-map-postgres docker/postgres && docker run -d --name dispatch-map-db -p 5432:5432 -v dispatch_map_pgdata:/var/lib/postgresql/data dispatch-map-postgres`)

### Running Services with `./run-dev.sh`

```bash
# Terminal 1 — API (FastAPI)
./run-dev.sh api

# Terminal 2 — Web (React / Vite)
./run-dev.sh web

# Terminal 3 — Consumer (Scraper worker)
./run-dev.sh consumer
```

Or run directly:

```bash
# API
uv run fastapi dev packages/api/main.py

# Web
npm install --prefix packages/web
npm run dev --prefix packages/web

# Consumer
uv run --directory packages/dispatch-consumer python main.py

# Migrations
uv run --directory packages/migrations alembic upgrade head
```

---

## Spec-Driven Development (SDD) Workflow

This project follows **Spec-Driven Development** to prevent contract drift between backend Python services and the frontend React application.

### Adding New Features with SDD (5-Step Lifecycle)

1. **Author the Feature Specification**:
   Copy the template and define requirements, boundaries, data models, and acceptance criteria:
   ```bash
   cp docs/specs/templates/feature_spec_template.md docs/specs/features/your-feature-name.md
   ```

2. **Define Schema & Database Contracts First**:
   - Add/update database tables in `packages/db/src/db/models.py`.
   - Add/update API models and routers in `packages/api/schemas.py` and `packages/api/routers/`.
   - If database models changed, create an Alembic migration:
     ```bash
     uv run --directory packages/migrations alembic revision --autogenerate -m "add feature tables"
     ```

3. **Synchronize Contracts Automatically (Never Manual Copying)**:
   Export the OpenAPI specification and regenerate TypeScript types:
   ```bash
   ./run-dev.sh spec:types
   ```
   This generates strict, compile-time TypeScript interfaces in `packages/web/src/types/api.generated.ts`.

4. **Write Tests Matching Acceptance Criteria**:
   - Add API endpoint test cases in `packages/api/tests/test_api.py`.
   - Add model invariants in `packages/db/tests/test_models.py`.
   - Add consumer parser tests in `packages/dispatch-consumer/tests/test_parser.py` if scraping logic changed.

5. **Implement Code & Verify Contracts**:
   Implement your frontend components and backend logic. Before committing, run the full verification suite:
   ```bash
   ./run-dev.sh spec:verify
   ```

See [docs/specs/README.md](docs/specs/README.md) for full details, templates, and conventions.

---

## Repository Structure

```
├── docker/
│   └── postgres/               # PostgreSQL Dockerfile and initialization SQL
├── packages/
│   ├── api/                    # FastAPI backend & production SPA host
│   ├── db/                     # Shared SQLModel database models package
│   ├── dispatch-consumer/      # Active calls scraper & geocoder worker
│   ├── migrations/             # Alembic database migrations
│   └── web/                    # React 19 + Vite frontend
├── .dockerignore               # Optimized Docker build context filter
├── .env.example                # Example environment variables
├── docker-compose.yml          # Local development Compose orchestration
├── docker-compose.prod.yml     # Production Compose orchestration
├── pyproject.toml              # Root uv workspace configuration
└── run-dev.sh                  # Development CLI runner
```
