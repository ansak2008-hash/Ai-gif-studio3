# Layer / Compositing Hardening Contract

## Scope
Harden the existing typed layer-compositing boundary without introducing a new rendering abstraction or changing blend formulas.

## Contract
1. BlendLayer is immutable at the record level and may contain only the existing RenderBuffer, BlendMode, and optional RenderMask contracts.
2. Composition consumes the iterable once, preserves declaration order exactly, and does not depend on object identity, hashing, or dictionary iteration.
3. Caller-owned RenderBuffers and RenderMasks are never mutated, and the returned RenderBuffer has independent storage.
4. An empty blend-layer iterable returns an independent copy of the base.
5. Base/source dimensions must match before rendering work begins.
6. A mask's spatial shape must match the RenderBuffer before blend evaluation; invalid masks must not cause a partially published output.
7. BlendModeEffect remains the sole owner of blend formulas; compositor orchestration must not duplicate formulas.
8. The compositor must remain deterministic for identical ordered inputs, including generator iterables.
9. Alpha boundaries of 0 and 1 must remain stable and finite; no implicit clipping, color conversion, or background replacement is introduced.
10. If a ResourceManager is supplied, the complete conservative working-set estimate is reserved before the first output allocation and released exactly on success or failure.
11. Resource admission failure must occur before output allocation and must leave caller inputs and resource accounting unchanged.
12. No registry, plugin, GPU abstraction, persistence schema, or new public layer model is introduced.

## Adversarial cases
- reversed layer order must produce a distinct result where blend semantics require it;
- generator and tuple inputs must produce identical results;
- repeated composition must not mutate source/base/mask;
- result storage must not alias caller-owned storage;
- zero-alpha and full-alpha source boundaries must remain deterministic;
- shape mismatch and invalid mask shape must fail before publishing output;
- insufficient resource budget must fail before RenderBuffer.copy/allocation;
- resource accounting must return to zero after injected blend failure.

## Gates
Contract -> adversarial tests -> minimal implementation -> unit/integration/determinism/security/Ruff -> CodeQL -> adversarial review -> merge.
