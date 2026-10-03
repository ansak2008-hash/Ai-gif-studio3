from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Protocol, runtime_checkable
from uuid import UUID


class DeliveryState(Enum):
    INTENT = "intent"
    SENT = "sent"
    FAILED = "failed"
    UNKNOWN = "unknown"
    TERMINAL = "terminal"


class SendDecision(Enum):
    SEND = "send"
    RETRY = "retry"
    SKIP_SENT = "skip_sent"
    HOLD_UNKNOWN = "hold"
    GIVE_UP = "give_up"


TERMINAL_STATES = {DeliveryState.SENT, DeliveryState.UNKNOWN, DeliveryState.TERMINAL}


@dataclass(frozen=True, slots=True)
class DeliveryConfig:
    max_attempts: int = 3

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")


@dataclass(frozen=True, slots=True)
class DeliveryIdentity:
    job_id: UUID
    artifact_id: UUID
    channel: str

    def __post_init__(self) -> None:
        if not self.channel:
            raise ValueError("channel must be non-empty")


@dataclass(frozen=True, slots=True)
class DeliveryRecord:
    identity: DeliveryIdentity
    state: DeliveryState
    attempt: int
    external_ref: Optional[str] = None
    error: Optional[str] = None

    def __post_init__(self) -> None:
        if self.attempt < 1:
            raise ValueError("attempt must be >= 1")
        if self.state is DeliveryState.SENT and not self.external_ref:
            raise ValueError("SENT requires external_ref")
        if self.state is DeliveryState.FAILED and not self.error:
            raise ValueError("FAILED requires error")
        if self.state in {DeliveryState.UNKNOWN, DeliveryState.TERMINAL} and not self.error:
            raise ValueError(f"{self.state.value.upper()} requires error")
        if self.state is not DeliveryState.SENT and self.external_ref is not None:
            raise ValueError("external_ref is only valid for SENT")


def begin_delivery(identity: DeliveryIdentity) -> DeliveryRecord:
    return DeliveryRecord(identity, DeliveryState.INTENT, attempt=1)


def mark_sent(rec: DeliveryRecord, external_ref: str) -> DeliveryRecord:
    if rec.state is not DeliveryState.INTENT:
        raise ValueError("only INTENT may transition to SENT")
    return DeliveryRecord(rec.identity, DeliveryState.SENT, rec.attempt, external_ref=external_ref)


def mark_failed(rec: DeliveryRecord, error: str) -> DeliveryRecord:
    if rec.state is not DeliveryState.INTENT:
        raise ValueError("only INTENT may transition to FAILED")
    return DeliveryRecord(rec.identity, DeliveryState.FAILED, rec.attempt, error=error)


def decide_send(
    rec: Optional[DeliveryRecord],
    config: DeliveryConfig,
) -> SendDecision:
    if rec is None:
        return SendDecision.SEND
    if rec.state is DeliveryState.SENT:
        return SendDecision.SKIP_SENT
    if rec.state is DeliveryState.UNKNOWN:
        return SendDecision.HOLD_UNKNOWN
    if rec.state is DeliveryState.TERMINAL:
        return SendDecision.GIVE_UP
    if rec.state is DeliveryState.FAILED:
        return SendDecision.RETRY if rec.attempt < config.max_attempts else SendDecision.GIVE_UP
    return SendDecision.HOLD_UNKNOWN


def begin_retry(
    rec: DeliveryRecord,
    config: DeliveryConfig,
) -> Optional[DeliveryRecord]:
    if rec.state is not DeliveryState.FAILED or rec.attempt >= config.max_attempts:
        return None
    return DeliveryRecord(rec.identity, DeliveryState.INTENT, rec.attempt + 1)


def mark_terminal(rec: DeliveryRecord, error: str) -> DeliveryRecord:
    if rec.state is not DeliveryState.FAILED:
        raise ValueError("only FAILED may transition to TERMINAL")
    return DeliveryRecord(rec.identity, DeliveryState.TERMINAL, rec.attempt, error=error)


def next_state_on_reobserve(rec: DeliveryRecord) -> DeliveryRecord:
    if rec.state is DeliveryState.INTENT:
        return DeliveryRecord(
            rec.identity,
            DeliveryState.UNKNOWN,
            rec.attempt,
            error="prior send outcome unknowable; manual resolution required",
        )
    return rec


@runtime_checkable
class DeliveryLogPort(Protocol):
    async def get(self, identity: DeliveryIdentity) -> Optional[DeliveryRecord]: ...

    async def begin_delivery(self, identity: DeliveryIdentity) -> DeliveryRecord: ...

    async def begin_retry(
        self, identity: DeliveryIdentity, max_attempts: int
    ) -> Optional[DeliveryRecord]: ...

    async def mark_sent(self, identity: DeliveryIdentity, external_ref: str) -> DeliveryRecord: ...

    async def mark_failed(self, identity: DeliveryIdentity, error: str) -> DeliveryRecord: ...

    async def mark_unknown(self, identity: DeliveryIdentity) -> DeliveryRecord: ...

    async def mark_terminal(self, identity: DeliveryIdentity, error: str) -> DeliveryRecord: ...
