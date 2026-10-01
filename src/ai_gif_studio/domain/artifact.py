from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4, uuid5


ARTIFACT_ID_NAMESPACE = UUID("a1e2b3c4-d5e6-7890-abcd-ef1234567890")


def make_artifact_id(job_id: UUID, artifact_type: str, storage_path: str) -> UUID:
    if not isinstance(job_id, UUID):
        raise TypeError(f"job_id must be UUID, got {type(job_id).__name__}")
    if not isinstance(artifact_type, str) or not artifact_type:
        raise ValueError("artifact_type must be non-empty string")
    if not isinstance(storage_path, str) or not storage_path:
        raise ValueError("storage_path must be non-empty string")
    return uuid5(ARTIFACT_ID_NAMESPACE, f"{job_id}|{artifact_type}|{storage_path}")


@dataclass(frozen=True, slots=True)
class Artifact:
    job_id: UUID
    type: str
    storage_path: str
    mime_type: str
    size_bytes: int
    sha256: str
    artifact_id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None
    metadata: dict[str, object] = field(default_factory=dict)
