# Running SpectrumSaber

## Prerequisites

- Docker and Docker Compose installed
- A `.env` file at the project root with database credentials (see `environments/local.env` for variable names)
- For local development without Docker: `uv` installed and a local PostgreSQL instance

---

## Django server (`server`)

The Django application exposes a GraphQL API at `/graphql/` and an Admin interface at `/admin/`.

### With Docker (recommended)

```bash
# Build images and start the app + database
make build

# Start app services only (after build)
make app

# Stop app services
make app-stop
```

Access:
- Admin UI: http://localhost:8000/admin/
- GraphQL playground: http://localhost:8000/graphql/

### Locally (without Docker)

> **Prerequisite:** the Docker database must be running (`make db` or `make app`) before running any local management commands. The app connects to Postgres on `localhost:5433`.

Prefer `make` targets — they load all required env files automatically:

```bash
# Apply migrations
make migrate

# Create a superuser
make createsuperuser

# Run the development server
make run
```

If running `uv` directly, include all three env files (omitting `common.env` causes missing `POSTGRES_DB` / `PYTHONPATH`):

```bash
uv run --env-file environments/common.env --env-file environments/local.env --env-file .env manage.py migrate
```

> **Never** run bare `python manage.py ...` — it will pick up the wrong `POSTGRES_HOST` and fail with permission errors against the system Postgres instead of the Docker one.

### First-time setup (after first `make app` or local start)

Run all first-time steps in one command:

```bash
make setup
```

This runs `migrate` → `createsuperuser` → `init_path_rules` (seeds the PathRule records required by all DAGs) in order.

### Useful management commands

```bash
# Open Django shell with all models auto-imported (shell_plus)
make shell

# Generate and apply database migrations after model changes
make migrations
make migrate
```

---

## Airflow ETL pipeline (`etl`)

Airflow orchestrates FTP ingestion. It provides a web UI to trigger DAGs and monitor runs.

### With Docker (recommended)

```bash
# Build images and start all Airflow services (scheduler, webserver, worker ×2, triggerer)
make build

# Start Airflow services only
make airflow

# Stop Airflow services
make airflow-stop
```

Access:
- Airflow UI: http://localhost:8080/ (default credentials: `airflow` / `airflow`)

### Running the whole stack at once

```bash
# Start both the app and Airflow together
make up

# Stop everything
make stop
```

### Triggering DAGs

Use the Airflow UI at http://localhost:8080/ or the REST API. The four ingestion DAGs run in order:

| DAG | Purpose | Key parameter |
|-----|---------|---------------|
| `process_coverage` | Scan FTP root, create `Coverage` records | — |
| `process_campaigns` | Scan campaigns under a coverage | `coverage_name` (default `AGRICULTURA`) |
| `process_data_points` | Scan data points under campaigns | `coverage_name` (default `HIDROLOGIA`) |
| `process_measurements` | Scan spectral files under data points | `coverage_name` (default `HIDROLOGIA`) |

Each DAG accepts a `force_reprocess` boolean (default `false`) to re-ingest already-scanned entries.

---

## CLI client (`spectrumsaber`)

The CLI client connects to the Django GraphQL API and optionally to the CONAE FTP server.

### Installation

The package is installed in editable mode inside Docker images automatically. For local use:

```bash
pip install -e .
# or with uv:
uv pip install -e .
```

### Interactive terminal UI

```bash
# Full Rich terminal shell (login, query, browse FTP)
spectrumsaber --interactive

# With a pre-configured provider for text-to-GraphQL
spectrumsaber --interactive --provider anthropic --api-key $ANTHROPIC_API_KEY
```

### Non-interactive (scripting / CI)

```bash
# Authenticate and run a query, save results to JSON
spectrumsaber \
  --username admin \
  --password secret \
  --query '{ coverages { id name } }' \
  --output results.json

# Load query from a file with variables
spectrumsaber \
  --username admin \
  --password secret \
  --query-file my_query.graphql \
  --variables-file vars.json \
  --output out.json

# Print the JWT token (useful for scripting)
spectrumsaber --username admin --password secret --show-token
```

### Text-to-GraphQL REPL

```bash
# Dedicated entry point
spectrumsaber-t2gql --provider anthropic --api-key $ANTHROPIC_API_KEY

# Or via the main command
spectrumsaber --text2gql --provider openai --api-key $OPENAI_API_KEY --model gpt-4o
```

Type a plain-English question at the prompt (e.g. `show me all campaigns from 2023`) and the tool will translate it to GraphQL, execute it, and display the result.

### Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GRAPHQL_ENDPOINT` | No | API URL (default `http://localhost:8000/graphql/`) |
| `GRAPHQL_JWT_TOKEN` | No | Skip login by providing a pre-existing JWT |
| `FTP_HOST` | For FTP commands | CONAE FTP server hostname |
| `FTP_USER` | For FTP commands | FTP username |
| `FTP_PASSWORD` | For FTP commands | FTP password |

Variables can be set in a `.env` file at the project root or exported in the shell.

---

## Running tests

```bash
# Run unit tests inside the testing Docker container
make test

# Generate coverage report
make coverage
```

Test configuration is in `tox.ini`. The testing profile starts a dedicated PostgreSQL container on port `9432`.

---

## Troubleshooting

### `relation "campaigns_pathrule" does not exist`

Migrations haven't been applied yet.

```bash
make migrate
```

### `permission denied for schema public` / `Unable to create the django_migrations table`

Caused by connecting to the wrong Postgres instance — typically the system Postgres instead of the Docker one, which happens when running bare `python manage.py` without the `local.env` env file (which sets `POSTGRES_HOST=localhost POSTGRES_PORT=5433`).

Fix: always use `make migrate` or the full `uv run` form with all three env files (see above). Never run `python manage.py` directly.
