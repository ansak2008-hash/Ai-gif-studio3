# AI GIF Studio — Architecture Baseline

> This document preserves the architecture/design baseline from PR #4 without reinterpretation.

## Architecture

The application uses a `src/` package and dependency inversion at its integration points:

```text
Telegram update → IntakeService → JobRepository → processing pipeline
                                      ↓
                                  SQLite/PostgreSQL
```

* `telegram/` owns aiogram routing and only translates Telegram updates to application calls.
* `services/` coordinates use cases and depends on repository protocols, not Telegram types.
* `models/` contains typed domain models; `schemas/` contains versioned, externally serializable contracts.
* Engine directories declare stable extension seams for the video, crop, composition, background, frame, motion, colour, and quality domains. Their first implementation must be a real processor—not a simulated success response.
* `database/` provides SQLAlchemy persistence behind a repository protocol. SQLite is the development default and the URL can be changed to PostgreSQL without changing callers.

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

`DesignSpec` and `ProcessingSettings` include an explicit `schema_version`. Their `from_payload` methods accept older versions and migrate them before validation. Future changes must add a migration rather than reinterpret old persisted JSON, preserving backwards compatibility.

## Processing pipeline

The target pipeline is: ingest → probe → crop choice (including **crop-only** mode) → compose → background/frame/motion → palette and quality validation → GIF encode → delivery. `ProcessingMode` already models `designed` and `crop_only`; implementing a mode means providing a real pipeline implementation and registering it through the service boundary.

## Design Engine

`DesignSpec` is the durable description of design intent: a 320×320 canvas default, crop policy, background, frame, motion, and colour policy. `ProcessingSettings` is operational output policy. Separating these allows presets and AI suggestions to change design intent without silently changing output-processing limits.

## Future extension points

* **Presets / projects / variations:** add versioned aggregates referencing immutable `DesignSpec` snapshots.
* **Undo/redo:** persist commands or revision chains per project rather than overwriting specs.
* **AI providers:** implement provider protocols in engine packages; providers receive typed input and return validated schema data.
* **Workers:** replace direct pipeline invocation with a queue consumer while preserving the `ProcessingJob` repository contract.
* **Database migrations:** introduce Alembic before the first schema migration in a deployed environment.

## Design contract snapshot

`DesignSpec` currently defines:

- 320×320 canvas by default
- crop policy: `center` or `smart`
- background style: `transparent`, `solid`, or `blurred`
- frame style: `none` or `rounded`
- motion style: `none` or `subtle`
- color policy: `source` or `adaptive`
- explicit schema versioning
- immutable/frozen validated model
- forbidden unknown fields

The source baseline is PR #4 of `ansak2008-hash/ai-gif-studio`, commit `689bd6fef2014c22f3726f21df4b088ab83bec83`.
