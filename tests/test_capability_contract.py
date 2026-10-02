from dataclasses import FrozenInstanceError

import pytest

from ai_gif_studio.application.capabilities import (
    Capability,
    CapabilityCollection,
    CapabilityState,
    CapabilityValidationError,
)


def make_available(**overrides):
    values = {
        "id": "resize",
        "state": CapabilityState.AVAILABLE,
        "input_domain": "project.image",
        "output_domain": "project.image",
        "execution_boundary": "project_editor",
        "contract_version": 1,
        "deterministic": True,
        "requirements": ("numpy",),
        "description": "Deterministic image resize.",
    }
    values.update(overrides)
    return Capability(**values)


def test_empty_identifier_is_rejected():
    with pytest.raises(CapabilityValidationError):
        make_available(id="   ")


def test_zero_contract_version_is_rejected():
    with pytest.raises(CapabilityValidationError):
        make_available(contract_version=0)


def test_planned_capability_cannot_be_executable():
    capability = Capability(
        id="future",
        state=CapabilityState.PLANNED,
        input_domain="project.image",
        output_domain="project.image",
        execution_boundary="project_editor",
        contract_version=1,
        deterministic=True,
    )

    with pytest.raises(CapabilityValidationError):
        capability.validate_input("project.image")


def test_available_capability_requires_complete_domains():
    with pytest.raises(CapabilityValidationError):
        make_available(input_domain="")


def test_incompatible_input_domain_fails_closed():
    capability = make_available()

    with pytest.raises(CapabilityValidationError):
        capability.validate_input("project.mask")


def test_compatible_input_domain_is_accepted():
    capability = make_available()

    capability.validate_input("project.image")


def test_version_mismatch_fails_closed():
    capability = make_available()

    with pytest.raises(CapabilityValidationError):
        capability.validate_input("project.image", contract_version=2)


def test_capability_is_immutable():
    capability = make_available()

    with pytest.raises(FrozenInstanceError):
        capability.id = "other"


def test_requirements_are_immutable():
    capability = make_available(requirements=["numpy", "opencv"])

    assert capability.requirements == ("numpy", "opencv")
    with pytest.raises(FrozenInstanceError):
        capability.requirements = ("numpy",)


def test_resource_metadata_is_declarative():
    capability = make_available(resource_requirements={"memory_bytes": 1024})

    assert capability.resource_requirements == (("memory_bytes", 1024),)


def test_collection_rejects_duplicate_identifiers():
    with pytest.raises(CapabilityValidationError):
        CapabilityCollection((make_available(), make_available()))


def test_collection_lookup_is_deterministic():
    resize = make_available()
    rotate = make_available(id="rotate")

    collection = CapabilityCollection((rotate, resize))

    assert collection.get("resize") is resize
    assert collection.get("rotate") is rotate


def test_collections_are_isolated():
    first = CapabilityCollection((make_available(),))
    second = CapabilityCollection((make_available(id="rotate"),))

    assert first.get("resize").id == "resize"
    assert second.get("rotate").id == "rotate"


def test_validation_does_not_mutate_editor_state():
    capability = make_available()

    state = {"revisions": 3}

    capability.validate_input("project.image", mutation_target=state)

    assert state == {"revisions": 3}


def test_requirement_text_is_declarative():
    capability = make_available(requirements=("shell:rm -rf",))

    assert capability.requirements == ("shell:rm -rf",)
