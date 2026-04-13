FROM apache/airflow:2.10.5

USER root
SHELL ["/bin/bash", "-c"]

# Install system dependencies
RUN apt-get update && apt-get install -y \
    graphviz \
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

RUN mkdir -p /app/project && chown -R ${USERNAME}:${GID} /app/project
COPY --chown=${USERNAME}:${GID} requirements.txt pyproject.toml /app/project/
WORKDIR /app/project
USER ${USERNAME}
RUN mkdir -p src/spectrumsaber && \
    touch src/spectrumsaber/__init__.py && \
    pip install -r requirements.txt && \
    pip install --no-deps -e .