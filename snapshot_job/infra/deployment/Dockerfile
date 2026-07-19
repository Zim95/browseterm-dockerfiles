FROM python:3.11-slim

RUN mkdir -p /app
COPY . /app
WORKDIR /app

RUN chmod +x ./infra/deployment/entrypoint.sh

# install system deps + docker
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    ca-certificates \
    apt-transport-https \
    gnupg \
    lsb-release \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# install poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:${PATH}"

# install dependencies
RUN poetry lock && poetry install --no-root

# Use the entrypoint script
ENTRYPOINT ["bash", "-c", "./infra/deployment/entrypoint.sh"]
