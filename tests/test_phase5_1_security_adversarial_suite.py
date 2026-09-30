from __future__ import annotations

import gc
import json
import os
import pickle
from pathlib import Path
from uuid import UUID

import pytest

from ai_gif_studio.domain.project import ProjectState
from ai_gif_studio.domain.specs import DesignSpec, ProcessingSettings

pytestmark = pytest.mark.unit

PROJECT_ID = UUID("12345678-1234-5678-1234-567812345678")


def make_state(metadata: dict | None = None) -> ProjectState:
    return ProjectState(
        PROJECT_ID,
        7,
        DesignSpec(),
        ProcessingSettings(),
        {} if metadata is None else metadata,
    )


class TestDeserializationInjectionAttacks:
    def test_json_payload_is_data_not_executable_code(self, tmp_path: Path) -> None:
        marker = tmp_path / "should_not_exist"
        malicious = {
            "project_id": str(PROJECT_ID),
            "revision": 7,
            "design": DesignSpec().model_dump(mode="json"),
            "processing": ProcessingSettings().model_dump(mode="json"),
            "metadata": {
                "__reduce__": ["os.system", [f"touch {marker}"]],
                "exploit": "import os; os.system('whoami')",
                "eval": "__import__('os').system('id')",
            },
        }
        restored = ProjectState.from_canonical_json(
            json.dumps(malicious, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        )
        assert restored.metadata["__reduce__"] == [
            "os.system",
            [f"touch {marker}"],
        ]
        assert not marker.exists()

    def test_pickle_payload_is_rejected_without_deserialization(self) -> None:
        class MaliciousPayload:
            def __reduce__(self):
                return (os.system, ("echo HACKED",))

        payload = pickle.dumps(MaliciousPayload())
        with pytest.raises(TypeError, match="canonical project state must be a string"):
            ProjectState.from_canonical_json(payload)  # type: ignore[arg-type]

    def test_invalid_utf8_surrogate_is_rejected(self) -> None:
        with pytest.raises(TypeError, match="UTF-8|JSON-compatible"):
            make_state({"bad": "\ud800"})


    def test_recursive_depth_attack_is_rejected_before_stack_exhaustion(self) -> None:
        payload = '{"nested":' * 200 + "null" + "}" * 200
        with pytest.raises(ValueError, match="depth|invalid canonical project state"):
            ProjectState.from_canonical_json(payload)


class TestResourceExhaustionAttacks:
    def test_oversized_json_payload_is_rejected_before_materialization(self) -> None:
        payload = (
            '{"project_id":"'
            + str(PROJECT_ID)
            + '","revision":7,"design":{},"processing":{},"metadata":{"blob":"'
            + ("x" * (8 * 1024 * 1024))
            + '"}}'
        )
        with pytest.raises(ValueError, match="maximum JSON payload size|invalid canonical"):
            ProjectState.from_canonical_json(payload)

    def test_repetitive_payload_is_bounded_without_huge_fixture(self) -> None:
        repeated = "A" * (256 * 1024)
        metadata = {"chunks": [repeated] * 32}
        with pytest.raises(ValueError, match="maximum JSON payload size"):
            make_state(metadata)

    def test_extreme_dimensions_remain_data_only(self) -> None:
        snapshot = make_state(
            {"width": 1_000_000, "height": 1_000_000, "channels": 4, "dtype": "float64"}
        )
        assert snapshot.metadata["width"] == 1_000_000
        assert snapshot.metadata["height"] == 1_000_000


class TestPathTraversalAttacks:
    @pytest.mark.parametrize(
        "malicious_path",
        [
            "../../../../etc/passwd",
            "..\\..\\Windows\\System32\\config\\SAM",
            "/etc/shadow",
            "C:\\Windows\\System32\\config\\SAM",
        ],
    )
    def test_paths_are_stored_as_opaque_data(self, malicious_path: str) -> None:
        snapshot = make_state({"asset_path": malicious_path})
        assert snapshot.metadata["asset_path"] == malicious_path

    def test_project_state_does_not_open_or_resolve_metadata_paths(
        self, tmp_path: Path
    ) -> None:
        target = tmp_path / "outside.txt"
        target.write_text("secret", encoding="utf-8")
        snapshot = make_state({"asset_path": str(target)})
        gc.collect()
        assert snapshot.metadata["asset_path"] == str(target)
        assert target.read_text(encoding="utf-8") == "secret"


class TestTypeConfusionAndLogicBypass:
    def test_wrong_top_level_types_are_rejected(self) -> None:
        with pytest.raises((TypeError, ValueError)):
            ProjectState(  # type: ignore[arg-type]
                "12345", 7, DesignSpec(), ProcessingSettings(), {}
            )
        with pytest.raises((TypeError, ValueError)):
            ProjectState(  # type: ignore[arg-type]
                PROJECT_ID, "7", DesignSpec(), ProcessingSettings(), {}
            )

    def test_boolean_revision_cannot_bypass_integer_contract(self) -> None:
        with pytest.raises(TypeError, match="revision must be an integer"):
            ProjectState(PROJECT_ID, True, DesignSpec(), ProcessingSettings(), {})

    def test_none_required_fields_are_rejected(self) -> None:
        with pytest.raises((TypeError, ValueError)):
            ProjectState(None, 7, DesignSpec(), ProcessingSettings(), {})  # type: ignore[arg-type]
        with pytest.raises((TypeError, ValueError)):
            ProjectState(PROJECT_ID, 7, None, ProcessingSettings(), {})  # type: ignore[arg-type]
        with pytest.raises((TypeError, ValueError)):
            ProjectState(PROJECT_ID, 7, DesignSpec(), ProcessingSettings(), None)  # type: ignore[arg-type]

    def test_non_mapping_metadata_is_rejected(self) -> None:
        with pytest.raises(TypeError, match="metadata must be a dictionary"):
            ProjectState(PROJECT_ID, 7, DesignSpec(), ProcessingSettings(), [])  # type: ignore[arg-type]

    def test_malformed_nested_spec_is_rejected(self) -> None:
        payload = json.loads(make_state().canonical_json)
        payload["design"]["unexpected"] = "attacker"
        payload["processing"]["unexpected"] = "attacker"
        tampered = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        with pytest.raises(ValueError, match="invalid canonical project state payload"):
            ProjectState.from_canonical_json(tampered)


class TestReverseSerializationBoundary:
    def test_non_string_serialization_inputs_are_never_unpickled(self) -> None:
        malicious_pickle = pickle.dumps({"command": "os.system", "args": ["id"]})
        for payload in (malicious_pickle, bytearray(malicious_pickle), memoryview(malicious_pickle)):
            with pytest.raises(TypeError):
                ProjectState.from_canonical_json(payload)  # type: ignore[arg-type]

    def test_duplicate_json_keys_are_rejected(self) -> None:
        attack = (
            '{"project_id":"'
            + str(PROJECT_ID)
            + '","revision":7,"revision":999,'
            + '"design":'
            + json.dumps(DesignSpec().model_dump(mode="json"), separators=(",", ":"))
            + ',"processing":'
            + json.dumps(ProcessingSettings().model_dump(mode="json"), separators=(",", ":"))
            + ',"metadata":{}}'
        )
        with pytest.raises(ValueError, match="duplicate|invalid canonical"):
            ProjectState.from_canonical_json(attack)


def test_phase5_1_security_gate_summary() -> None:
    snapshot = make_state({"security": "adversarial", "unicode": "مرحبا 🚀"})
    restored = ProjectState.from_canonical_json(snapshot.canonical_json)
    assert restored.canonical_json == snapshot.canonical_json
    assert restored.metadata["security"] == "adversarial"
