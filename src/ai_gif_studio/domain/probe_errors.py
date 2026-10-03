from __future__ import annotations

"""Classified probe failure contract.

Only ProbeError subclasses are expected, containable probe failures.
Unexpected exceptions must propagate to expose programming and environment bugs.
"""


class ProbeError(Exception):
    """Base class for expected, containable probe failures."""


class ProbeFileNotFoundError(ProbeError):
    """The input media file is missing or unreadable."""


class ProbeCorruptMediaError(ProbeError):
    """The media could not be parsed as valid media."""


class ProbeTimeoutError(ProbeError):
    """The probe exceeded its configured time budget."""


class ProbeResourceLimitError(ProbeError):
    """The probe rejected media for a configured resource limit."""


class ProbeExecutionError(ProbeError):
    """The probe process failed for an unclassified execution reason."""
