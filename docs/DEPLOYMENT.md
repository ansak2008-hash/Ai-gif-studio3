# Runtime Deployment

## Services

Run three runtime components:

1. **Telegram intake** — starts `ai-gif-studio`; validates the incoming file and creates a durable queued job.
2. **Arq worker** — runs `ai_gif_studio.infrastructure.worker.WorkerSettings` and performs FFmpeg processing outside the Telegram update handler.
3. **Redis** — queue transport only. Generated media belongs in the Artifact Registry storage directory, not Redis.

## Required environment

Copy `.env.example` to `.env` and set:

- `TELEGRAM_BOT_TOKEN`
- `APP_REDIS_URL`
- `APP_DATABASE_URL`
- `APP_TEMP_DIRECTORY`
- `APP_STORAGE_DIRECTORY`

Optionally set `TELEGRAM_ALLOWED_USER_IDS` as a comma-separated allowlist.

## Local startup

Install Python 3.11+, FFmpeg/ffprobe and Redis, then:

```bash
pip install -e .
ai-gif-studio
```

In a second process, start the Arq worker with the project's `WorkerSettings`.

For production, use PostgreSQL instead of SQLite and run the worker as a separate unprivileged process/container.

## Resource controls

The application enforces upload-size, duration, resolution and worker-timeout limits from configuration. FFmpeg is invoked with argument arrays rather than shell command strings.

For production media processing:

- run as a non-root user;
- use a dedicated writable temp/artifact volume;
- disable unnecessary network egress from the worker;
- apply CPU/memory/process limits at the container or service-manager level;
- keep Redis private;
- back up PostgreSQL and artifact storage according to retention requirements.

## Health endpoints

The HTTP adapter exposes `GET /health` for liveness and `GET /ready` for the readiness contract.

## Licensing gate

Do not enable an AI model in production until its code license, exact weight source, weight hash, redistribution terms and commercial-use terms are recorded in `docs/MODEL_REGISTRY.md`.


## Docker Compose production runtime

The repository includes a production-oriented Compose topology with four services:

- **telegram**: Telegram polling intake only; it does not render media.
- **worker**: Arq worker with FFmpeg; media processing is isolated from Telegram update handling.
- **redis**: queue transport only.
- **postgres**: durable production database.

Before startup, copy `.env.production.example` to `.env`, set `TELEGRAM_BOT_TOKEN` and a strong `POSTGRES_PASSWORD`, and keep `.env` out of version control.

Build and start:

```bash
docker compose up -d --build
```

The Telegram and worker containers run as the unprivileged `app` user, use read-only root filesystems, and receive dedicated writable artifact/temp volumes. Redis and PostgreSQL remain internal to the Compose network.

For a first deployment, verify the worker and Telegram service logs, then send a small test video through the bot and confirm the resulting GIF is delivered. Do not expose Redis or PostgreSQL ports publicly.
