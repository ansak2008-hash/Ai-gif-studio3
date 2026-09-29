from __future__ import annotations

import copy
import gc
import hashlib
import json
import math
import random
from uuid import UUID

import numpy as np
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


def make_deep_mutable_structure(depth: int = 5, width: int = 3) -> dict:
    if depth == 0:
        return {"value": 0.123456789, "list": [1, 2, 3], "nested": {"enabled": True}}
    return {
        f"layer_{index}": make_deep_mutable_structure(depth - 1, width)
        for index in range(width)
    }


def leaf(structure: dict, depth: int) -> dict:
    current = structure
    for _ in range(depth):
        current = current["layer_0"]
    return current


def assert_json_safe(value: object) -> None:
    encoded = json.dumps(value, ensure_ascii=False, allow_nan=False)
    assert json.loads(encoded) == value


class TestMutationNuclearStrike:
    def test_direct_attribute_assignment_is_rejected(self) -> None:
        snapshot = make_state()
        with pytest.raises((AttributeError, TypeError)):
            snapshot.revision = 99  # type: ignore[misc]

    def test_private_storage_assignment_is_rejected(self) -> None:
        snapshot = make_state()
        with pytest.raises((AttributeError, TypeError)):
            snapshot._canonical_json = "{}"  # type: ignore[misc]

    def test_deep_nested_source_mutation_cannot_reach_snapshot(self) -> None:
        source = make_deep_mutable_structure()
        snapshot = make_state(source)
        source_leaf = leaf(source, 5)
        source_leaf["value"] = 999.0
        source_leaf["list"].append("attacker")
        source_leaf["nested"]["enabled"] = False

        snapshot_leaf = leaf(snapshot.metadata, 5)
        assert snapshot_leaf["value"] != 999.0
        assert "attacker" not in snapshot_leaf["list"]
        assert snapshot_leaf["nested"]["enabled"] is True

    def test_nested_accessor_mutation_cannot_reach_snapshot(self) -> None:
        snapshot = make_state(make_deep_mutable_structure())
        view_leaf = leaf(snapshot.metadata, 5)
        view_leaf["value"] = 999.0
        view_leaf["list"].append("attacker")
        view_leaf["nested"]["enabled"] = False

        fresh_leaf = leaf(snapshot.metadata, 5)
        assert fresh_leaf["value"] != 999.0
        assert "attacker" not in fresh_leaf["list"]
        assert fresh_leaf["nested"]["enabled"] is True

    def test_design_accessor_is_detached(self) -> None:
        snapshot = make_state()
        design = snapshot.design
        design.layers.append(
            {"type": "shape", "color": "#ffffff", "opacity": 1.0, "thickness": 3}
        )
        assert snapshot.design.layers == []

    def test_processing_accessor_is_detached(self) -> None:
        snapshot = make_state()
        first = snapshot.processing
        second = snapshot.processing
        assert first is not second
        assert first.model_dump(mode="json") == second.model_dump(mode="json")

    def test_deepcopy_does_not_create_shared_mutable_state(self) -> None:
        snapshot = make_state({"nested": {"values": [1, 2, 3]}})
        cloned = copy.deepcopy(snapshot)
        cloned.metadata["nested"]["values"].append(999)
        assert snapshot.metadata == {"nested": {"values": [1, 2, 3]}}

    def test_gc_does_not_corrupt_detached_reads(self) -> None:
        snapshot = make_state({"nested": {"value": 42}})
        view = snapshot.metadata
        for _ in range(3):
            gc.collect()
        assert view["nested"]["value"] == 42
        assert snapshot.project_id == PROJECT_ID


class TestSerializationDeterminismStress:
    def test_float_precision_chaos_is_bit_deterministic(self) -> None:
        metadata = {
            "pi_approx": 3.141592653589793238462643383279,
            "tiny": 1e-300,
            "huge": 1e300,
            "negative_zero": -0.0,
        }
        first = make_state(metadata).canonical_json.encode("utf-8")
        second = make_state(copy.deepcopy(metadata)).canonical_json.encode("utf-8")
        assert first == second
        assert hashlib.sha256(first).digest() == hashlib.sha256(second).digest()
        restored = make_state(metadata).metadata
        assert all(math.isfinite(restored[key]) for key in metadata)

    def test_non_finite_numeric_payload_is_rejected(self) -> None:
        for value in (float("nan"), float("inf"), float("-inf")):
            with pytest.raises(TypeError):
                make_state({"bad": value})

    def test_dict_key_order_attack_is_normalized(self) -> None:
        keys = [f"key_{index:04d}" for index in range(100)]
        random.Random(1337).shuffle(keys)
        messy = {key: index for index, key in enumerate(keys)}
        reversed_insertion = dict(reversed(list(messy.items())))
        first = make_state(messy).canonical_json
        second = make_state(reversed_insertion).canonical_json
        assert first == second
        parsed = json.loads(first)
        expected = json.dumps(
            parsed, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        assert first == expected

    def test_unicode_and_control_characters_round_trip_exactly(self) -> None:
        malicious_strings = [
            "Line\u2028Break",
            "Tab\u0009Here",
            "Null\u0000Byte",
            "Emoji🚀💀",
            "Arabicمرحبا",
            "RTL\u200FText",
        ]
        snapshot = make_state({"strings": malicious_strings})
        restored = ProjectState.from_canonical_json(snapshot.canonical_json)
        assert restored.metadata["strings"] == malicious_strings
        assert restored.canonical_json == snapshot.canonical_json

    def test_canonical_json_is_utf8_and_reproducible(self) -> None:
        snapshot = make_state({"unicode": "مرحبا 🚀", "nested": {"z": 2, "a": 1}})
        encoded = snapshot.canonical_json.encode("utf-8")
        assert encoded.decode("utf-8") == snapshot.canonical_json
        assert encoded == make_state(snapshot.metadata).canonical_json.encode("utf-8")


class TestReferenceIsolation:
    def test_no_shared_mutable_reference_with_source(self) -> None:
        source = {"layers": [{"values": [1, 2, 3]}]}
        snapshot = make_state(source)
        source["layers"][0]["values"][0] = 999
        source["layers"].append({"values": [4]})
        assert snapshot.metadata == {"layers": [{"values": [1, 2, 3]}]}

    def test_numpy_like_attack_is_rejected_at_boundary(self) -> None:
        array = np.arange(16, dtype=np.float32).reshape(2, 2, 4)
        with pytest.raises(TypeError):
            make_state({"array": array})

    def test_unsupported_mutable_structure_is_rejected(self) -> None:
        with pytest.raises(TypeError):
            make_state({"set": {1, 2, 3}})

    def test_state_survives_source_deallocation(self) -> None:
        source = {"payload": {"values": [1, 2, 3]}}
        snapshot = make_state(source)
        del source
        gc.collect()
        assert snapshot.metadata == {"payload": {"values": [1, 2, 3]}}


class TestEdgeCaseResilience:
    def test_empty_metadata_state_round_trip(self) -> None:
        snapshot = make_state({})
        restored = ProjectState.from_canonical_json(snapshot.canonical_json)
        assert restored.metadata == {}
        assert restored.design.layers == []
        assert restored.project_id == PROJECT_ID
        assert restored.revision == 7

    def test_large_but_bounded_metadata_round_trip(self) -> None:
        metadata = {
            "layers": [{"id": index, "data": "x" * 1000} for index in range(1000)],
            "big": "y" * 100_000,
        }
        snapshot = make_state(metadata)
        restored = ProjectState.from_canonical_json(snapshot.canonical_json)
        assert restored.metadata == metadata

    @pytest.mark.parametrize(
        "malformed",
        [
            "{",
            "[]",
            "null",
            "42",
            json.dumps({"project_id": str(PROJECT_ID)}),
            json.dumps(
                {
                    "project_id": str(PROJECT_ID),
                    "revision": True,
                    "design": DesignSpec().model_dump(mode="json"),
                    "processing": ProcessingSettings().model_dump(mode="json"),
                    "metadata": {},
                }
            ),
        ],
    )
    def test_malformed_canonical_payload_is_rejected(self, malformed: str) -> None:
        with pytest.raises((TypeError, ValueError)):
            ProjectState.from_canonical_json(malformed)

    def test_noncanonical_json_is_rejected(self) -> None:
        snapshot = make_state({"a": 1, "b": 2})
        payload = json.loads(snapshot.canonical_json)
        noncanonical = json.dumps(
            {
                "metadata": payload["metadata"],
                "project_id": payload["project_id"],
                "revision": payload["revision"],
                "design": payload["design"],
                "processing": payload["processing"],
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
        assert noncanonical != snapshot.canonical_json
        with pytest.raises(ValueError):
            ProjectState.from_canonical_json(noncanonical)

    def test_duplicate_json_key_attack_is_rejected(self) -> None:
        snapshot = make_state({"safe": True})
        attack = snapshot.canonical_json.replace(
            '"revision":7}', '"revision":7,"revision":7}', 1
        )
        with pytest.raises(ValueError):
            ProjectState.from_canonical_json(attack)


def test_phase5_1_final_gatekeeper_integrity() -> None:
    metadata = {
        "nested": make_deep_mutable_structure(depth=3, width=3),
        "unicode": "مرحبا 🚀\u0000",
        "numbers": [0.0, -0.0, 1e-300, 1e300],
    }
    snapshot = make_state(metadata)

    with pytest.raises((AttributeError, TypeError)):
        snapshot.revision = 999  # type: ignore[misc]

    assert snapshot.canonical_json.encode("utf-8") == snapshot.canonical_json.encode("utf-8")
    restored = ProjectState.from_canonical_json(snapshot.canonical_json)
    assert restored.canonical_json == snapshot.canonical_json

    detached = restored.metadata
    detached_leaf = leaf(detached["nested"], 3)
    detached_leaf["value"] = 123456
    assert leaf(restored.metadata["nested"], 3)["value"] != 123456
    assert_json_safe(restored.metadata)
