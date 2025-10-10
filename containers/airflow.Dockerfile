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

# Create user
ARG GID=0
ARG USERNAME=airflow

RUN mkdir -p /app && chown -R ${USERNAME}:${GID} /app
RUN chown -R ${USERNAME}:${GID} /home/${USERNAME}
ENV HOME=/home/${USERNAME}

COPY requirements.txt .
USER ${USERNAME}
RUN pip install -r requirements.txt
WORKDIR /app/project