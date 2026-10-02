from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType


class CapabilityValidationError(ValueError):
    """Raised when a capability contract is invalid or incompatible."""

class CapabilityState(StrEnum):
    AVAILABLE = "available"
    PLANNED = "planned"

VALID_DOMAINS = frozenset(
    {
        "project.image",
        "project.mask",
        "render.buffer",
        "render.mask",
    }
)
VALID_EXECUTION_BOUNDARIES = frozenset(
    {
        "project_editor",
        "render",
        "application",
    }
)

def _validate_text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CapabilityValidationError(f"{field} must be a non-empty string")
    return value

def _normalize_requirements(requirements: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    normalized = tuple(requirements)
    if any(not isinstance(item, str) or not item.strip() for item in normalized):
        raise CapabilityValidationError("requirements must contain non-empty strings")
    return normalized

def _normalize_resources(
    resource_requirements: dict[str, int] | tuple[tuple[str, int], ...],
) -> tuple[tuple[str, int], ...]:
    items = (
        tuple(resource_requirements.items())
        if isinstance(resource_requirements, dict)
        else tuple(resource_requirements)
    )
    normalized: list[tuple[str, int]] = []
    for name, value in items:
        _validate_text(name, "resource requirement name")
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise CapabilityValidationError(
                "resource requirement values must be non-negative integers"
            )
        normalized.append((name, value))
    return tuple(normalized)

@dataclass(frozen=True, slots=True)
class Capability:
    id: str
    state: CapabilityState
    input_domain: str = ""
    output_domain: str = ""
    execution_boundary: str = ""
    contract_version: int = 1
    deterministic: bool = True
    requirements: tuple[str, ...] = ()
    resource_requirements: tuple[tuple[str, int], ...] = ()
    description: str = ""

    def __post_init__(self) -> None:
        _validate_text(self.id, "id")
        if not isinstance(self.state, CapabilityState):
            raise CapabilityValidationError("state must be a CapabilityState")
        if (
            isinstance(self.contract_version, bool)
            or not isinstance(self.contract_version, int)
            or self.contract_version < 1
        ):
            raise CapabilityValidationError("contract_version must be a positive integer")
        if not isinstance(self.deterministic, bool):
            raise CapabilityValidationError("deterministic must be a boolean")
        requirements = _normalize_requirements(self.requirements)
        resources = _normalize_resources(self.resource_requirements)
        object.__setattr__(self, "requirements", requirements)
        object.__setattr__(self, "resource_requirements", resources)
        if self.state is CapabilityState.AVAILABLE:
            self._validate_complete_contract()
        else:
            if self.input_domain:
                self._validate_domain(self.input_domain, "input_domain")
            if self.output_domain:
                self._validate_domain(self.output_domain, "output_domain")
            if self.execution_boundary:
                self._validate_boundary(self.execution_boundary)

    def _validate_complete_contract(self) -> None:
        self._validate_domain(self.input_domain, "input_domain")
        self._validate_domain(self.output_domain, "output_domain")
        self._validate_boundary(self.execution_boundary)

    @staticmethod
    def _validate_domain(domain: str, field: str) -> None:
        _validate_text(domain, field)
        if domain not in VALID_DOMAINS:
            raise CapabilityValidationError(f"unknown {field}: {domain}")

    @staticmethod
    def _validate_boundary(boundary: str) -> None:
        _validate_text(boundary, "execution_boundary")
        if boundary not in VALID_EXECUTION_BOUNDARIES:
            raise CapabilityValidationError(f"unknown execution_boundary: {boundary}")

    def validate_input(self, domain: str, *, contract_version: int | None = None) -> None:
        if self.state is not CapabilityState.AVAILABLE:
            raise CapabilityValidationError("planned capabilities are not executable")
        self._validate_domain(domain, "input_domain")
        if domain != self.input_domain:
            raise CapabilityValidationError(
                f"incompatible input domain: expected {self.input_domain}, received {domain}"
            )
        if contract_version is not None:
            if (
                isinstance(contract_version, bool)
                or not isinstance(contract_version, int)
                or contract_version != self.contract_version
            ):
                raise CapabilityValidationError("incompatible contract version")

    def validate_output(self, domain: str, *, contract_version: int | None = None) -> None:
        if self.state is not CapabilityState.AVAILABLE:
            raise CapabilityValidationError("planned capabilities are not executable")
        self._validate_domain(domain, "output_domain")
        if domain != self.output_domain:
            raise CapabilityValidationError(
                f"incompatible output domain: expected {self.output_domain}, received {domain}"
            )
        if contract_version is not None:
            if (
                isinstance(contract_version, bool)
                or not isinstance(contract_version, int)
                or contract_version != self.contract_version
            ):
                raise CapabilityValidationError("incompatible contract version")

class CapabilityCollection:
    __slots__ = ("_items", "_by_id", "_locked")

    def __init__(self, capabilities: tuple[Capability, ...]) -> None:
        items = tuple(capabilities)
        if any(not isinstance(item, Capability) for item in items):
            raise CapabilityValidationError("capabilities must contain Capability objects")
        by_id: dict[str, Capability] = {}
        for capability in items:
            if capability.id in by_id:
                raise CapabilityValidationError(
                    f"duplicate capability identifier: {capability.id}"
                )
            by_id[capability.id] = capability
        object.__setattr__(self, "_items", items)
        object.__setattr__(self, "_by_id", MappingProxyType(by_id))
        object.__setattr__(self, "_locked", True)

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_locked", False):
            raise AttributeError("CapabilityCollection is immutable")
        object.__setattr__(self, name, value)

    def get(self, capability_id: str) -> Capability:
        _validate_text(capability_id, "capability_id")
        try:
            return self._by_id[capability_id]
        except KeyError as exc:
            raise CapabilityValidationError(f"unknown capability: {capability_id}") from exc

    def items(self) -> tuple[tuple[str, Capability], ...]:
        return tuple((capability.id, capability) for capability in self._items)

    def __iter__(self) -> Iterator[Capability]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

def _available(
    name: str,
    requirements: tuple[str, ...],
    description: str = "",
    *,
    execution_boundary: str = "project_editor",
) -> Capability:
    return Capability(
        id=name,
        state=CapabilityState.AVAILABLE,
        input_domain="project.image",
        output_domain="project.image",
        execution_boundary=execution_boundary,
        requirements=requirements,
        description=description,
    )

CAPABILITIES = CapabilityCollection(
    (
        _available(
            "crop",
            ("opencv", "numpy"),
            "Deterministic center/fill/fit crop with focus control.",
        ),
        _available("resize", ("ffmpeg",)),
        _available(
            "transform",
            ("opencv", "numpy"),
            "Deterministic bounded image/frame transformation chains.",
        ),
        _available(
            "warp",
            ("opencv", "numpy"),
            "Deterministic affine and four-point perspective transforms.",
        ),
        _available(
            "blend",
            ("opencv", "numpy"),
            "Masked normal, multiply, screen, and additive compositing.",
            execution_boundary="render",
        ),
        _available(
            "color_grade",
            ("numpy",),
            "Deterministic LUT-style brightness, contrast, saturation, temperature, tint, levels, and gamma grading.",
            execution_boundary="render",
        ),
        _available("compose", ("composition-engine",)),
        _available("motion", ("ffmpeg",), "Bounded float/pan motion."),
        _available("layers", ("ffmpeg",), "Bounded decorative layers."),
        _available("text", ("ffmpeg-drawtext",), "Bounded text overlay."),
        _available(
            "typography",
            ("ffmpeg-drawtext",),
            "Arabic/Latin typography with bounded materials and depth.",
        ),
        _available("frames", ("ffmpeg-drawbox",), "Deterministic decorative frame presets."),
        _available("backgrounds", ("ffmpeg",), "Deterministic background presets."),
        _available(
            "presets",
            ("design-spec-v3",),
            "Eight deterministic, allowlisted design presets.",
        ),
        _available(
            "quality_gate",
            ("ffmpeg",),
            "Adaptive FPS and output validation.",
        ),
    )
    + tuple(
        Capability(
            id=name,
            state=CapabilityState.PLANNED,
            requirements=("ai-provider", "verified-weights"),
        )
        for name in (
            "background_remove",
            "background_replace",
            "object_remove",
            "inpaint",
            "upscale",
            "interpolate",
            "style",
            "relight",
            "expand",
        )
    )
)
