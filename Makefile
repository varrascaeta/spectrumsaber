# Makefile for managing SpectrumSaber services and Django commands
# Usage: make <target>
# Targets:
#   shell            - Open Django shell with environment variables
#   migrations      - Create new Django migrations
#   migrate         - Apply Django migrations
#   createsuperuser - Create a Django superuser
#   airflow         - Start Airflow services using Docker Compose
#   app             - Start the main application services using Docker Compose

CLIENT_CONTAINER=spark-client
ENVIRONMENT=environments/local.env
ENV_CFG=--env-file $(ENVIRONMENT) --env-file secrets.env
DJANGO_PREFIX=uv run $(ENV_CFG) service/manage.py

shell:
	uv run $(ENV_CFG) service/manage.py shell_plus
migrations:
	uv run $(ENV_CFG) service/manage.py makemigrations
migrate:
	uv run $(ENV_CFG) service/manage.py migrate
createsuperuser:
	uv run $(ENV_CFG) service/manage.py createsuperuser --noinput
airflow:
	docker compose --env-file environments/production.env --env-file secrets.env --profile airflow up -d
app:
	docker compose --env-file environments/production.env --env-file secrets.env --profile app up -d
app-stop:
	docker compose --env-file environments/production.env --env-file secrets.env --profile app down
airflow-stop:
	docker compose --env-file environments/production.env --env-file secrets.env --profile airflow down