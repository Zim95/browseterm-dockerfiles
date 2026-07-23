FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1

RUN mkdir -p /app
COPY . /app
WORKDIR /app

RUN chmod +x ./infra/deployment/entrypoint.sh

# build tooling for grpcio + git for the git deps
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# install poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:${PATH}"

# install dependencies
RUN poetry lock && poetry install --no-root

ENTRYPOINT ["bash", "-c", "./infra/deployment/entrypoint.sh"]
