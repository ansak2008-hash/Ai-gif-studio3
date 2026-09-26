# AI Creative GIF Studio

Production-oriented modular monolith for Telegram video-to-GIF processing.

## Current implementation
- **Crop Only** is a real FFmpeg pipeline: centered six-second window, square crop, 320×320 Lanczos scaling, palette generation, GIF encoding, size validation and FPS fallback ladder.
- **Design GIF foundation** preserves the PR2 composition engine and adds a dependency-free square composition adapter.
- **Job lifecycle** uses durable queued/processing/completed/failed states and checkpoint-ready step records.
- **Artifact Registry** tracks UUID-backed files, MIME type, size, SHA-256 and metadata; Redis is never used for file storage.
- **DesignSpec / ProcessingSettings** are separate versioned documents.
- **Capability Engine / Workflow Engine** are explicit registries rather than unstructured dictionaries.
- **FFmpegService** owns process execution and does not accept shell command strings.
- **SQLite + SQLAlchemy 2.x** is the development persistence layer; PostgreSQL is supported by changing the database URL.
- **Alembic** migration scaffolding is included.
- **Redis + Arq** is the queue boundary; workers are separate from Telegram update handling.
- **FastAPI** exposes real /health and /ready endpoints.
- **Model Registry / GPUResourceManager / AIProvider** are implemented as extension boundaries.
- Background Removal is **not falsely marked production-ready**: no model is activated until the exact code and weight licenses and SHA-256 provenance are verified.

## Architecture
Interfaces (Telegram / HTTP / future CLI) → Application → Domain → Infrastructure

Telegram handlers validate and enqueue; processing happens in workers. Engines do not import Telegram.

## Run locally
Requirements: Python 3.11+, FFmpeg/ffprobe and Redis for queued processing.
Install with a Python 3.11 virtual environment, pip install -e '.[dev]', and copy .env.example to .env.
Set TELEGRAM_BOT_TOKEN. For the queue worker, start Redis and run an Arq worker using ai_gif_studio.infrastructure.worker.WorkerSettings. The development database is SQLite.

## Testing
ruff check .
pytest -q
The integration test generates a synthetic MP4 with FFmpeg and exercises the actual video-to-GIF path. It is skipped only when FFmpeg is unavailable.

## Security
See docs/SECURITY.md. Production should run workers as an unprivileged user inside a resource-limited container with network egress disabled for media processing.

## Model licensing gate
See docs/MODEL_REGISTRY.md. Code and weight licenses are recorded separately; exact weights must be hash-pinned before activation.

## Legacy PR reconciliation
PR1 supplied the central render configuration contract; PR2 supplied the smart square composition algorithm; PR3 supplied the real crop-only FFmpeg strategy; PR4 supplied the Python modular foundation. Useful concepts are preserved rather than blindly merged, while the final runtime is consolidated around Python, domain/application boundaries, queue workers and infrastructure adapters.