# PR #3 — Standalone Crop Only GIF Engine

Source: `ansak2008-hash/ai-gif-studio`
Commit: `d42da6c9e27f3ec57ff51c6dc8abe2e5873b3553`

## Motivation

- Provide a focused, non-design conversion path that turns arbitrary video into a true 1:1 cropped, high-quality 320×320 GIF without stretching, frames, backgrounds, or design effects.
- Meet practical constraints needed for downstream callers (Telegram bot): default 6s output, preserve important pixels where possible, use an FPS ladder to satisfy a 2,400,000 byte hard limit, and avoid low-quality intermediate frames.

## Description

- Add a new `crop_only_engine` package exposing `crop_video_to_gif(...)` and `CropOnlyResult`/`CropOnlyError` for a clear, callable API.
- Implement `CropOnlyConfiguration` in `config.py` to enforce `320` output, default `6.0s` duration, `max_output_bytes`, palette size, and an ordered descending `fps_ladder`.
- Implement the conversion pipeline in `engine.py` which probes the source with `ffprobe`, selects the temporal centre segment, performs a true centred-square crop (`crop='min(iw,ih)'`), Lanczos `scale` to `320:320`, generates a per-output palette with `palettegen` and applies `paletteuse` with `sierra2_4a` dithering, and iterates the configured FPS ladder until the GIF is under the size limit; write is atomic on success.
- Add tests in `tests/test_engine.py` validating the ffmpeg filter graph, six-second centred window and FPS fallback behaviour, configuration validation, and failure when the size limit cannot be met.

## Testing

- Ran `python -m pytest -q` and all tests passed (`4 passed`).
- Ran `python -m compileall -q crop_only_engine` which succeeded without errors.
- Ran `git diff --check` which reported no issues, and the added tests exercise the pipeline, duration selection, ladder fallback, and size-limit failure.
