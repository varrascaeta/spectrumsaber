FROM python:3.12.8-slim-bullseye
SHELL ["/bin/bash", "-c"]
EXPOSE 8000
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

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
RUN uv pip install --system -r requirements.txt