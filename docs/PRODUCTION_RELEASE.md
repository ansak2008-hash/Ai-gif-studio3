# Production Release Gate

Six phases are now represented as explicit engineering gates.

1. Quality intelligence: adaptive FPS fallback and final probe-based quality report.
2. DesignSpec intake and persistence: every job stores versioned design and processing intent; authenticated API endpoints can update them.
3. Capability/workflow integration: deterministic capabilities are explicit; unsupported AI capabilities stay gated.
4. AI capability boundary: provider/model execution requires verified weights and licensing metadata.
5. Security and observability: API key protection, request IDs, bounded specs, queue/resource limits, timed job steps, and artifact quality metadata.
6. Production release: CI lint/tests, migration reproducibility, dependency review, and security scanning are release requirements.

External references used during implementation include official FFmpeg filter documentation, Alembic asyncio guidance, FastAPI security guidance, Arq retry documentation, and GitHub supply-chain/security guidance.

No model weights are activated solely because they are publicly available. Activation requires exact source, exact weight source, license decision, and verification evidence.
