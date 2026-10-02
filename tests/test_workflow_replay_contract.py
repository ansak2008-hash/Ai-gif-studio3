from __future__ import annotations

import json
from uuid import uuid4

import pytest

from ai_gif_studio.application.workflow_replay import (
    Workflow,
    WorkflowOperation,
    WorkflowReplayError,
    replay_workflow,
)
from ai_gif_studio.domain.commands import ReplaceDesignSpecCommand
from ai_gif_studio.domain.project import ProjectState
from ai_gif_studio.domain.specs import DesignSpec, ProcessingSettings
from ai_gif_studio.services.project_editor import ProjectEditor

pytestmark = pytest.mark.unit


def _state() -> ProjectState:
    return ProjectState(
        uuid4(),
        0,
        DesignSpec(),
        ProcessingSettings(),
        {"fixture": "phase-6-4"},
    )


def _operation(color: str, index: int) -> WorkflowOperation:
    return WorkflowOperation(
        capability_id="design.replace",
        capability_version=1,
        payload={"color": color, "nested": {"index": index}},
        metadata={"operation": "replace_design", "index": index},
    )


def _workflow(*operations: WorkflowOperation) -> Workflow:
    return Workflow("background-sequence", 1, operations)


def _resolver(operation: WorkflowOperation):
    color = operation.payload["color"]
    return ReplaceDesignSpecCommand(
        DesignSpec(background={"mode": "solid", "color": color})
    )


def test_empty_identifiers_are_rejected() -> None:
    with pytest.raises(ValueError, match="identifier"):
        Workflow("", 1, ())


def test_invalid_versions_are_rejected() -> None:
    for version in (0, -1, True):
        with pytest.raises(ValueError, match="version"):
            Workflow("workflow", version, ())


def test_operation_invalid_version_is_rejected() -> None:
    with pytest.raises(ValueError, match="version"):
        WorkflowOperation("design.replace", 0, {}, {})


def test_workflow_and_operations_are_immutable() -> None:
    operation = _operation("#111111", 1)
    workflow = _workflow(operation)

    with pytest.raises((AttributeError, TypeError)):
        workflow.operations += (operation,)
    with pytest.raises((AttributeError, TypeError)):
        operation.capability_id = "other"


def test_input_mutation_cannot_change_workflow() -> None:
    payload = {"nested": {"value": 1}}
    metadata = {"nested": {"value": 2}}
    operation = WorkflowOperation("test", 1, payload, metadata)
    payload["nested"]["value"] = 99
    metadata["nested"]["value"] = 99

    assert operation.payload["nested"]["value"] == 1
    assert operation.metadata["nested"]["value"] == 2


def test_operation_order_is_preserved() -> None:
    workflow = _workflow(_operation("#111111", 1), _operation("#222222", 2))

    assert [item.payload["color"] for item in workflow.operations] == [
        "#111111",
        "#222222",
    ]


def test_canonical_encoding_is_deterministic() -> None:
    first = _workflow(_operation("#111111", 1))
    second = _workflow(
        WorkflowOperation(
            "design.replace",
            1,
            {"nested": {"index": 1}, "color": "#111111"},
            {"index": 1, "operation": "replace_design"},
        )
    )

    assert first.canonical_json == second.canonical_json


def test_decode_reencode_is_byte_for_byte_canonical() -> None:
    workflow = _workflow(_operation("#111111", 1))
    document = workflow.canonical_json

    restored = Workflow.from_canonical_json(document)

    assert restored.canonical_json == document
    assert restored == workflow


def test_duplicate_json_keys_are_rejected() -> None:
    document = '{"contract_version":1,"id":"x","id":"y","operations":[]}'

    with pytest.raises(ValueError, match="duplicate"):
        Workflow.from_canonical_json(document)


def test_unknown_top_level_fields_are_rejected() -> None:
    document = '{"contract_version":1,"id":"x","operations":[],"extra":1}'

    with pytest.raises(ValueError, match="top-level"):
        Workflow.from_canonical_json(document)


def test_non_finite_json_numbers_are_rejected() -> None:
    document = (
        '{"contract_version":1,"id":"x","operations":['
        '{"capability_id":"test","capability_version":1,'
        '"metadata":{"value":NaN},"payload":{}}]}'
    )

    with pytest.raises(ValueError, match="non-finite"):
        Workflow.from_canonical_json(document)


@pytest.mark.asyncio
async def test_replay_resolves_and_commits_in_workflow_order() -> None:
    workflow = _workflow(
        _operation("#111111", 1),
        _operation("#222222", 2),
        _operation("#333333", 3),
    )
    editor = ProjectEditor.create(_state())
    resolved: list[int] = []

    def resolver(operation: WorkflowOperation):
        resolved.append(operation.payload["nested"]["index"])
        return _resolver(operation)

    result = replay_workflow(editor, workflow, resolver)

    assert result.committed_operations == 3
    assert resolved == [1, 2, 3]
    assert editor.revision_count == 4
    assert editor.current_state.design.background["color"] == "#333333"


def test_replay_is_equivalent_for_same_initial_state_and_resolver() -> None:
    workflow = _workflow(
        _operation("#111111", 1),
        _operation("#222222", 2),
    )
    first = ProjectEditor.create(_state())
    second = ProjectEditor.from_canonical_json(first.canonical_json)

    replay_workflow(first, workflow, _resolver)
    replay_workflow(second, workflow, _resolver)

    assert first.canonical_json == second.canonical_json


def test_failed_operation_preserves_committed_prefix() -> None:
    workflow = _workflow(
        _operation("#111111", 1),
        _operation("#222222", 2),
        _operation("#333333", 3),
    )
    editor = ProjectEditor.create(_state())
    attempted: list[int] = []

    def resolver(operation: WorkflowOperation):
        index = operation.payload["nested"]["index"]
        attempted.append(index)
        if index == 2:
            raise RuntimeError("resolver failure")
        return _resolver(operation)

    with pytest.raises(WorkflowReplayError) as caught:
        replay_workflow(editor, workflow, resolver)

    error = caught.value
    assert error.operation_index == 1
    assert error.committed_operations == 1
    assert attempted == [1, 2]
    assert editor.revision_count == 2
    assert editor.current_state.design.background["color"] == "#111111"
    assert isinstance(error.__cause__, RuntimeError)


def test_command_failure_does_not_create_failed_revision() -> None:
    workflow = _workflow(_operation("#111111", 1))
    editor = ProjectEditor.create(_state())

    def resolver(_operation: WorkflowOperation):
        class FailingCommand:
            def apply(self, _state: ProjectState) -> ProjectState:
                raise RuntimeError("command failure")

        return FailingCommand()

    with pytest.raises(WorkflowReplayError) as caught:
        replay_workflow(editor, workflow, resolver)

    assert caught.value.operation_index == 0
    assert caught.value.committed_operations == 0
    assert editor.revision_count == 1
    assert caught.value.__cause__ is not None


def test_later_operations_are_not_attempted_after_failure() -> None:
    workflow = _workflow(
        _operation("#111111", 1),
        _operation("#222222", 2),
        _operation("#333333", 3),
    )
    editor = ProjectEditor.create(_state())
    attempted: list[int] = []

    def resolver(operation: WorkflowOperation):
        index = operation.payload["nested"]["index"]
        attempted.append(index)
        if index == 2:
            raise RuntimeError("stop")
        return _resolver(operation)

    with pytest.raises(WorkflowReplayError):
        replay_workflow(editor, workflow, resolver)

    assert attempted == [1, 2]


def test_executable_looking_strings_remain_inert_data() -> None:
    operation = WorkflowOperation(
        "safe",
        1,
        {"value": "python -c \"raise RuntimeError()\""},
        {"provider": "import os; os.system('x')"},
    )
    workflow = _workflow(operation)

    payload = json.loads(workflow.canonical_json)
    assert payload["operations"][0]["payload"]["value"].startswith("python -c")
    assert payload["operations"][0]["metadata"]["provider"].startswith("import os")


def test_workflow_does_not_change_when_payload_result_is_mutated() -> None:
    operation = _operation("#111111", 1)
    workflow = _workflow(operation)
    payload = operation.payload
    payload["nested"]["index"] = 999

    assert workflow.operations[0].payload["nested"]["index"] == 1
