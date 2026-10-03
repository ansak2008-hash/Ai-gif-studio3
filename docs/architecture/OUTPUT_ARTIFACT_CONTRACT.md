# Output Artifact Contract

Status: active contract.

## Scope

This contract defines the default GIF output constraints at the rendering boundary. It closes specification drift between the documented product requirements and the current render configuration/quality ladder.

## Contract

1. The canonical output canvas is exactly 320x320 pixels.
2. The default output duration is exactly 6.0 seconds, subject to the existing shorter-input behavior.
3. The hard maximum output size is 2,400,000 bytes. An output above this limit is invalid.
4. The canonical normal FPS fallback ladder is exactly 30, 27, 24, 20, 18, 15 FPS, in descending order.
5. The default preferred FPS is 30 FPS.
6. Quality fallback may only descend through the canonical ladder. A caller requesting a non-ladder FPS remains an explicit/custom input and does not silently rewrite that input to a different FPS.
7. The GIF palette limit is at most 256 colors.
8. Scaling to the canonical canvas uses Lanczos where the existing render path performs scaling.
9. Output validation must verify the produced artifact, not only the requested configuration.
10. This contract does not change existing public constructor shapes, persisted schema versions, or unrelated rendering formulas.

## Adversarial cases

- exact 320x320 dimensions are accepted;
- any other output dimensions are rejected;
- exact 2,400,000-byte output is accepted;
- 2,400,001-byte output is rejected;
- default duration is exactly 6.0 seconds;
- default FPS is exactly 30;
- default fallback order is exactly 30, 27, 24, 20, 18, 15;
- fallback never increases FPS after a lower preferred value is supplied;
- non-ladder explicit FPS values remain explicit rather than being silently normalized;
- palette configuration cannot exceed 256 colors;
- the quality ladder is deterministic and contains no duplicate FPS values.

## Non-goals

- no GIF encoder replacement;
- no new rendering abstraction;
- no Telegram delivery changes;
- no background/frame/calligraphy feature changes;
- no persistence schema migration;
- no automatic normalization of invalid caller input.

## Gates

Contract -> adversarial tests -> minimal implementation -> local compile/lint/tests -> CI -> CodeQL -> adversarial review -> compatibility/architecture review -> merge -> post-merge verification.
