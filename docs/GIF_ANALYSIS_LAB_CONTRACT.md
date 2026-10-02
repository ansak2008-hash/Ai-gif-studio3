# GIF Analysis Lab Contract

## Purpose

The GIF Analysis Lab is a deterministic, offline-capable inspection utility for reference GIFs. It extracts measurable media facts and conservative motion signals without modifying the source artifact.

The tool is an analysis instrument, not a renderer, optimizer, encoder, or design generator.

## Contract

1. Input is either a local GIF file or an in-memory byte payload.
2. The source bytes are never modified.
3. Every decoded frame is normalized to RGB for analysis.
4. Reported dimensions come from the decoded GIF canvas.
5. Frame count is the number of successfully decoded frames.
6. Frame durations are preserved in milliseconds and total duration is their sum.
7. Effective FPS is reported as `1000 / mean_frame_duration_ms`; zero or missing durations are a validation failure.
8. The `loop_count` field reports the raw GIF loop-extension value; `0` means infinite looping and does not mean zero playback loops.
9. File size is measured from the original source bytes when bytes are available.
10. Adjacent-frame motion is the mean absolute per-channel pixel difference over the full RGB frame.
11. First-to-last difference is reported as a loop-boundary signal only. It is not declared to be a loop-quality score.
12. Corner samples are reported individually and their arithmetic mean is reported as a background-color heuristic. This value must be labeled heuristic because corners can contain foreground content, gradients, shadows, or effects.
13. The analyzer reports palette cardinality for each decoded frame and the maximum observed cardinality.
14. The analyzer reports timing uniformity and an exact duration histogram so variable-frame-rate GIFs are visible.
15. The analyzer reports per-frame motion statistics and their aggregate mean, maximum, and percentile values (P25/P50/P75/P90/P95/P99).
16. The analyzer is deterministic for identical input bytes and configuration.
17. Analysis failures are explicit typed errors; partial fabricated reports are forbidden.
18. The core analyzer must not require network access. URL retrieval belongs only to the bounded URL adapter.
19. No new runtime dependency may be introduced. Existing Pillow and NumPy dependencies are sufficient.
20. The analyzer must not introduce registries, plugins, schedulers, rendering abstractions, or persistence changes.
21. The output schema is versioned and JSON-serializable.

## Security and resource boundaries

- Maximum source bytes are bounded by the caller.
- Canvas pixels, decoded frame count, and cumulative decoded pixels are bounded by the caller.
- Decoding is streaming with bounded retained frame memory rather than retaining the entire animation as decoded images.
- URL retrieval has a finite timeout and bounded chunked response size.
- The core analyzer does not execute external commands.
- Malformed GIFs and invalid resource limits must fail closed.
- Reports must not embed raw frame data or source bytes.

## Non-goals

- Semantic object recognition.
- Optical flow.
- Automatic design classification.
- Perceptual similarity scoring.
- GIF re-encoding.
- Declaring a GIF seamless from first/last frame difference alone.

## Proof obligations

Tests must cover:
- valid single and multi-frame GIFs;
- exact duration accounting;
- deterministic repeated analysis;
- motion calculations and percentiles;
- loop-boundary signal semantics;
- per-frame and maximum decoded palette cardinality;
- variable timing and exact duration histogram;
- corner-color heuristic;
- malformed/empty input rejection;
- input and decoded-resource size limits;
- invalid configuration rejection;
- bounded URL adapter behavior and over-limit response rejection;
- JSON serialization;
- no source mutation;
- no frame-array leakage in the report.

## Extension boundary

Future deeper analysis may add explicit modules for:
- spatial motion localization;
- temporal phase detection;
- alpha/transparency inspection;
- text/layout geometry;
- color quantization pressure;
- perceptual loop analysis.

Each extension requires its own contract and adversarial tests before implementation.
