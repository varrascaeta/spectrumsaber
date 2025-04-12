# SpectrumSaber Project Setup
# ==========================

## Installation

Python version: 3.12

On linux:
1. Install python3.12
    ```bash
    sudo apt-get install python3.12 python3.12-dev
    ```
2. Install `uv` dependency manager (docs[ here](https://docs.astral.sh/uv/getting-started/installation/))
    ```bash
    wget -qO- https://astral.sh/uv/install.sh | sh
    ```
3. Clone the spectrumsaber repository to your local machine. You can use the following command:
    ```bash
    git clone https://github.com/varrascaeta/spectrumsaber.git
    ```
4. Navigate to the directory where you cloned the repository:
    ```bash
    cd spectrumsaber
    ```
5. Install dependencies using `uv`:
    ```bash
    uv sync
    ```
    This will create a new virtual environment at `.venv`

6. Install docker and docker compose plugin (example for Ubuntu)
    ```bash
    # Add Docker's official GPG key:
    sudo apt-get update
    sudo apt-get install ca-certificates curl
    sudo install -m 0755 -d /etc/apt/keyrings
    sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    sudo chmod a+r /etc/apt/keyrings/docker.asc

    # Add the repository to Apt sources:
    echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | \
    sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update
    ```
    And then:
    ```bash
    sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    ```

