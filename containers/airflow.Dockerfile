FROM apache/airflow:2.10.2

USER root
SHELL ["/bin/bash", "-c"]

# Install system dependencies
RUN apt-get update && apt-get install -y \
    pkg-config \
    libxml2-dev \
    libxmlsec1-dev \
    libssl-dev \
    libffi-dev \
    gcc \
    libc-dev \
    make \
    curl \
    ca-certificates

# Download the latest installer
ADD https://astral.sh/uv/install.sh /uv-installer.sh

# Run the installer then remove it
RUN sh /uv-installer.sh && rm /uv-installer.sh

# Ensure the installed binary is on the `PATH`
ENV PATH="/root/.local/bin/:$PATH"


COPY pyproject.toml /app/
WORKDIR /app
ENV PYTHONPATH=/app
RUN uv export > requirements.txt
USER airflow
RUN pip install --no-cache-dir "apache-airflow==2.10.2" -r requirements.txt
