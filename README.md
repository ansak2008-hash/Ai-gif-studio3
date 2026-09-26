# AI GIF Studio

AI GIF Studio is a Python 3.11+ foundation for an extensible Telegram service that turns a
user-provided video into a professional 320×320 GIF. The initial delivery deliberately
establishes durable boundaries, persisted job intake, schemas, and configuration before
implementing visual effects or GIF-quality tuning.

## Architecture

The application uses a `src/` package and dependency inversion at its integration points:

```text
Telegram update → IntakeService → JobRepository → processing pipeline
                                      ↓
                                  SQLite/PostgreSQL
```

* `telegram/` owns aiogram routing and only translates Telegram updates to application calls.
* `services/` coordinates use cases and depends on repository protocols, not Telegram types.
* `models/` contains typed domain models; `schemas/` contains versioned, externally serializable
  contracts.
* Engine directories declare stable extension seams for the video, crop, composition,
  background, frame, motion, colour, and quality domains. Their first implementation must be a
  real processor—not a simulated success response.
* `database/` provides SQLAlchemy persistence behind a repository protocol. SQLite is the
  development default and the URL can be changed to PostgreSQL without changing callers.

## Project layout

| Directory | Responsibility |
| --- | --- |
| `telegram/` | Bot creation, routing, and Telegram-specific presentation. |
| `video_processing/` | Video probes, decoding, encoding, and orchestration contracts. |
| `crop_engine/` | Crop calculation and future subject-aware crop providers. |
| `composition_engine/` | Canvas/layout decisions and DesignSpec interpretation. |
| `background_engine/` | Background generation and compositing providers. |
| `frame_engine/` | Borders, safe areas, and frame rendering. |
| `motion_engine/` | Temporal effects and animation policies. |
| `color_intelligence/` | Palette extraction and contrast decisions. |
| `quality_engine/` | Output validation and quality policies. |
| `configuration/` | One centralized typed settings source. |
| `database/` | Database session, ORM records, and repositories. |
| `logging/` | Structured logging setup. |
| `models/`, `schemas/`, `services/`, `utilities/` | Domain types, contracts, use cases, and shared helpers. |
| `tests/` | Fast contract and persistence tests. |

## Versioned contracts

`DesignSpec` and `ProcessingSettings` include an explicit `schema_version`. Their `from_payload`
methods accept older versions and migrate them before validation. Future changes must add a
migration rather than reinterpret old persisted JSON, preserving backwards compatibility.

## Configuration and environment variables

Configuration is read once from `.env` and the environment by `AppSettings`.

| Variable | Purpose | Default |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | Bot token (required to run polling). | — |
| `TELEGRAM_ALLOWED_USER_IDS` | Optional comma-separated allowlist. | Empty (allow all) |
| `APP_ENVIRONMENT` | Environment label. | `development` |
| `APP_LOG_LEVEL` | Python log level. | `INFO` |
| `APP_DATABASE_URL` | SQLAlchemy async database URL. | SQLite under `data/` |
| `APP_TEMP_DIRECTORY` | Per-job workspace parent. | `./data/tmp` |
| `APP_MAX_UPLOAD_BYTES` | Intake limit. | `52428800` |
| `APP_FFMPEG_BINARY` | Future encoder executable location. | `ffmpeg` |

Copy `.env.example` to `.env`; never commit tokens.

## Installation

```bash
python3.11 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
```

## Running

Set `TELEGRAM_BOT_TOKEN` in `.env`, then run:

```bash
ai-gif-studio
```

The application creates its database tables and starts long polling. `/start` explains the
current intake capability. Sending a video creates a durable `received` job after size and
allowlist checks. The bot intentionally does **not** claim conversion is complete until a real
processing pipeline is connected.

## Telegram integration

`telegram.router.create_router` handles `/start` and videos. Authorization and file-size limits
are application configuration, while Telegram file metadata is converted into a domain
`VideoSubmission`. This keeps a future webhook adapter or a non-Telegram API independent of
aiogram.

## Processing pipeline

The target pipeline is: ingest → probe → crop choice (including **crop-only** mode) → compose →
background/frame/motion → palette and quality validation → GIF encode → delivery. `ProcessingMode`
already models `designed` and `crop_only`; implementing a mode means providing a real pipeline
implementation and registering it through the service boundary.

## Design Engine

`DesignSpec` is the durable description of design intent: a 320×320 canvas default, crop policy,
background, frame, motion, and colour policy. `ProcessingSettings` is operational output policy.
Separating these allows presets and AI suggestions to change design intent without silently
changing output-processing limits.

## Future extension points

* **Presets / projects / variations:** add versioned aggregates referencing immutable
  `DesignSpec` snapshots.
* **Undo/redo:** persist commands or revision chains per project rather than overwriting specs.
* **AI providers:** implement provider protocols in engine packages; providers receive typed input
  and return validated schema data.
* **Workers:** replace direct pipeline invocation with a queue consumer while preserving the
  `ProcessingJob` repository contract.
* **Database migrations:** introduce Alembic before the first schema migration in a deployed
  environment.

## Development checks

```bash
ruff check .
pytest
```
