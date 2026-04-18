# Makefile for managing SpectrumSaber services and Django commands
# Usage: make <target> [ARGS="..."] [SERVICE="..."]

# ─── Environment configuration ────────────────────────────────────────────────
# Docker Compose CLI env (variable substitution in compose file)
DOCKER_ENV  = --env-file environments/common.env \
              --env-file environments/docker.env \
              --env-file .env

TEST_ENV    = --env-file environments/common.env \
              --env-file environments/testing.env \
              --env-file .env

# uv run env (injected into the local process)
LOCAL_ENV   = --env-file environments/common.env \
              --env-file environments/local.env \
              --env-file .env

DC          = docker compose $(DOCKER_ENV)
DC_TEST     = docker compose $(TEST_ENV)
DJANGO      = uv run $(LOCAL_ENV) manage.py

# ─── Local development ────────────────────────────────────────────────────────

run:              ## Run the Django dev server locally
	$(DJANGO) runserver

shell:            ## Open Django shell_plus locally
	$(DJANGO) shell_plus

migrations:       ## Create new Django migrations
	$(DJANGO) makemigrations

migrate:          ## Apply Django migrations
	$(DJANGO) migrate

createsuperuser:  ## Create a Django superuser (uses DJANGO_SUPERUSER_* from .env)
	$(DJANGO) createsuperuser --noinput

# ─── CLI client ───────────────────────────────────────────────────────────────

client:           ## Run the spectrumsaber CLI  (usage: make client ARGS="--query '...'")
	uv run $(LOCAL_ENV) spectrumsaber $(ARGS)

client-interactive: ## Run the spectrumsaber CLI in interactive mode
	uv run $(LOCAL_ENV) spectrumsaber --interactive

t2gql:            ## Start the text-to-GraphQL REPL  (usage: make t2gql ARGS="--model gpt-4o")
	uv run $(LOCAL_ENV) spectrumsaber-t2gql $(ARGS)

# ─── Docker Compose: all services ─────────────────────────────────────────────

build:            ## Build images and start all services (app + airflow)
	uv export --format requirements-txt --no-hashes --no-header -o requirements.txt && \
	$(DC) --profile app --profile airflow up --build -d

up:               ## Start all services without rebuilding
	$(DC) --profile app --profile airflow up --scale airflow-worker=2 -d

stop:             ## Stop all services
	$(DC) --profile app --profile airflow down

logs:             ## Tail logs (usage: make logs SERVICE=airflow-scheduler)
	$(DC) logs -f $(SERVICE)

ps:               ## Show status of all running services
	$(DC) ps

# ─── Docker Compose: app only ─────────────────────────────────────────────────

app:              ## Start the app services (Django + DB)
	$(DC) --profile app up -d

app-stop:         ## Stop the app services
	$(DC) --profile app down

app-build:        ## Build and start the app services
	$(DC) --profile app up --build -d

# ─── Docker Compose: Airflow only ─────────────────────────────────────────────

airflow:          ## Start the Airflow services
	$(DC) --profile airflow up --scale airflow-worker=2 -d

airflow-stop:     ## Stop the Airflow services
	$(DC) --profile airflow down

airflow-build:    ## Build and start the Airflow services
	$(DC) --profile airflow up --build -d

# ─── Testing ──────────────────────────────────────────────────────────────────

test:             ## Run tests (spins up test DB in Docker, then runs tox)
	$(DC_TEST) --profile testing up -d && tox -e py312

coverage:         ## Run coverage report via tox
	tox -e coverage

lint:             ## Run flake8 style checks via tox
	tox -e style

# ─── Packaging ────────────────────────────────────────────────────────────────

requirements:     ## Export requirements.txt from the uv lockfile
	uv export --format requirements-txt --no-hashes --no-header -o requirements.txt

# ─── Help ─────────────────────────────────────────────────────────────────────

help:             ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help

.PHONY: run shell migrations migrate createsuperuser \
        client client-interactive t2gql \
        build up stop logs ps \
        app app-stop app-build \
        airflow airflow-stop airflow-build \
        test coverage lint \
        requirements help
