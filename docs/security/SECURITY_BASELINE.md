# Security Baseline Contract

## Purpose

The security baseline protects untrusted application inputs and the software supply chain without coupling security infrastructure to the rendering implementation.

## Scope

This baseline applies before untrusted media reaches the temporal/rendering engine and to CI dependency/secret checks.

### Trust boundary

External HTTP, Telegram, and file inputs are untrusted. They must pass the existing request-size boundary and any media-specific validation before decoding or rendering. Rendering stages consume trusted internal representations such as ManuscriptAsset and RenderBuffer.

### Required controls

1. CI must scan repository content for accidental secrets.
2. CI must audit Python dependencies for known published vulnerabilities.
3. Media validation must be performed before expensive decode/render work and must enforce bounded resources (bytes, dimensions, and where applicable frame count/duration).
4. Security validation must be deterministic and covered by regression tests.
5. Security controls must not duplicate or bypass canonical RenderBuffer/ManuscriptAsset contracts.

## Non-goals for this baseline

No custom cryptography, obfuscation, anti-debugging, IDS, MFA, runtime sandbox, or licensing policy is introduced by this document.

## Change gate

Security changes follow the repository engineering protocol: Contract -> Tests -> Implementation -> CI -> Adversarial Review -> Merge.
