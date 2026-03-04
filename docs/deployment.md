# Deployment

This document explains how to deploy and operate `polymarket-liquidity-bot-suite`
in local and production-like environments.


## Local development

### Prerequisites

- Python 3.11+
- A virtual environment (recommended)
- Access to Polymarket Builder/Relayer credentials (for live or sandbox use)

### Steps

1. Clone the repository and install dependencies:

   ```bash
   pip install -e ".[dev]"
   ```

2. Copy the environment template:

   ```bash
   cp .env.example .env
   ```

3. Fill in `.env` with:
   - Polymarket API base URLs.
   - Builder and Relayer credentials.
   - Database URL.

4. Initialize the database and (optionally) run migrations:

   ```bash
   python -m polymarket_bot.storage.db init
   ```

5. Run tests:

   ```bash
   pytest
   ```

6. Start a simple strategy in dry-run mode:

   ```bash
   polymarket-bot run-strategy mm-spread-tightener \
     --config ./config/mm_spread_tightener.example.yaml \
     --dry-run
   ```

7. Start the web dashboard:

   ```bash
   polymarket-bot web
   ```


## Docker deployment

The repository includes a `Dockerfile` and `docker-compose.yml` that can be used to
run the bot engine and web UI in containers.

### Dockerfile (high level)

The `Dockerfile`:

- Uses a slim Python 3.11 base image.
- Installs system dependencies for Python and database drivers.
- Copies project files and installs the package with `[dev]` extras if needed.
- Sets a default command to run the bot engine.

### docker-compose

`docker-compose.yml` (or `compose.yml`) describes a multi-service setup:

- **`bot`**
  - Runs the main engine (e.g., `polymarket-bot run-all`).
  - Mounts configuration and `.env`.
  - Depends on the database service.

- **`web`**
  - Runs the FastAPI dashboard (e.g., `polymarket-bot web`).
  - Shares database and configuration with `bot`.

- **`db`**
  - Optional Postgres service if you do not want to use SQLite.

You can adapt these services for your target environment (Kubernetes, Nomad, etc.).


### Example usage

1. Build images:

   ```bash
   docker compose build
   ```

2. Start services:

   ```bash
   docker compose up -d
   ```

3. Tail logs:

   ```bash
   docker compose logs -f bot
   docker compose logs -f web
   ```

4. Access the web dashboard at:

   - `http://localhost:8000` (by default)


## Production considerations

### Secrets and configuration

- Use a secure secrets manager (e.g., AWS Secrets Manager, GCP Secret Manager, Vault)
  instead of plain `.env` files for production deployments.
- Mount or inject environment variables into containers at runtime.


### Scaling and reliability

- For high-throughput operation:
  - Consider running multiple strategy processes with distinct strategy sets or markets.
  - Use a robust database backend (e.g., Postgres) instead of local SQLite.
- Use process supervisors (systemd, Kubernetes deployments, Nomad jobs, etc.) to:
  - Restart failed containers.
  - Deploy updates with rolling strategies.


### Observability

- Configure logging to:
  - Emit structured logs (JSON) for easier ingestion.
  - Include strategy names, market IDs, order IDs, and tx hashes where applicable.
- Optionally enable:
  - Prometheus metrics endpoint from the web app.
  - Dashboards in Grafana or a similar tool.


### Safety and risk

- Always start new configurations in **dry-run mode** and inspect:
  - Strategy behavior.
  - Generated orders.
  - Risk metrics and PnL.
- Tighten risk limits (`MAX_DAILY_TX`, `MAX_DAILY_NOTIONAL`, etc.) for initial
deployments and loosen them gradually as you observe stable behavior.


## Scripts

The `scripts/` directory contains helper scripts for common workflows:

- **`run_bot.sh`**
  - Starts the main execution engine with a provided config directory.

- **`run_dev_server.sh`**
  - Starts the FastAPI web dashboard and optionally a sandbox strategy in dry-run mode.

- **`seed_example_config.py`**
  - Populates a `config/` directory with example YAML configs for each strategy.

You can adapt these scripts or translate them into platform-specific equivalents
for your deployment environment.

