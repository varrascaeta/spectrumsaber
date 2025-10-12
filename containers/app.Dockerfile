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
ARG GID=0
ARG UID=1000
# This should match the POSTGRES_USER in secrets.env
ARG USERNAME=spectrumsaber

RUN useradd -m -s /bin/bash -u ${UID} -g ${GID} ${USERNAME}
RUN mkdir -p /app && chown -R ${USERNAME}:${GID} /app
RUN chown -R ${USERNAME}:${GID} /home/${USERNAME}
ENV HOME=/home/${USERNAME}

COPY requirements.txt .
USER ${USERNAME}
RUN pip install -r requirements.txt
WORKDIR /app/project