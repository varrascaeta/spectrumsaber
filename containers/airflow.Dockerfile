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
ARG UID=1001
ARG USERNAME=airflow

RUN useradd -m -u ${UID} -s /bin/bash ${USERNAME}
RUN mkdir -p /app && chown -R ${USERNAME}:${USERNAME} /app
USER ${USERNAME}
ENV HOME=/home/${USERNAME}
WORKDIR /app/project

# Download the latest installer
ADD https://astral.sh/uv/install.sh /uv-installer.sh

# Run the installer then remove it
RUN sh /uv-installer.sh && rm /uv-installer.sh

# Ensure the installed binary is on the `PATH`
ENV PATH="/root/.local/bin/:$PATH"

COPY pyproject.toml /app/project/pyproject.toml
ENV PYTHONPATH=/app/project:$PYTHONPATH
RUN uv export > requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
