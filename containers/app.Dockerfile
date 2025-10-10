FROM python:3.12.8-slim-bullseye
SHELL ["/bin/bash", "-c"]
EXPOSE 8000
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

USER root

RUN apt-get update && apt-get upgrade -y
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
ARG UID=1001
ARG USERNAME=appuser

RUN useradd -m -u ${UID} -s /bin/bash ${USERNAME}

RUN mkdir -p /app && chown -R ${USERNAME}:${USERNAME} /app

ENV HOME=/home/${USERNAME}
WORKDIR /app/project

# Download and install uv package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
    
# Ensure the installed binary is on the `PATH`
ENV PATH="$HOME/.local/bin:$PATH"
COPY pyproject.toml /app/project/pyproject.toml
WORKDIR /app/project
ENV PYTHONPATH=/app/project:$PYTHONPATH
RUN uv export > requirements.txt
RUN uv pip install --system -r requirements.txt
USER ${USERNAME}