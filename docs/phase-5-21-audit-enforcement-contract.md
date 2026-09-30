# Phase 5.21 Audit Enforcement Contract

## Scope
Convert confirmed audit findings into enforceable engineering constraints without implementing unrelated future features.

## Contract
1. Database model declarations MUST import successfully under the supported SQLAlchemy 2.x version.
2. SQLAlchemy-reserved declarative attribute names MUST NOT be used as Python model attributes.
3. Existing database column names remain stable unless a migration contract explicitly changes them.
4. CI MUST enforce both Ruff linting and Ruff formatting verification.
5. The database contract test MUST verify importability and the public Python attribute used for JSON metadata.
6. No new runtime dependency, rendering algorithm, or speculative architecture is introduced by this hardening change.
7. Verification order is Contract -> Tests -> Implementation -> CI/CodeQL -> adversarial review.

## Confirmed audit disposition
- M2 (metadata declarative attribute): confirmed and treated as a real import-time SQLAlchemy compatibility defect.
- CI formatting enforcement: confirmed gap; pre-commit exists, but CI currently runs only ruff check .
- C3/C4, M4, M10: stale against current main and are not implemented.
- C1 algorithm proposals: future design input only; not implemented here.

## Compatibility decision
The Python attribute is renamed to metadata_json while preserving the physical SQL column name metadata. This removes the SQLAlchemy reserved-name collision without forcing a database schema rename.
