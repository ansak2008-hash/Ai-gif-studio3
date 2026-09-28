"""Deterministic single-output render graph over canonical RenderBuffer values."""
from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from .render_buffer import RenderBuffer
from .render_mask import RenderMask
from .selective_region import SelectiveRegionEffect

RenderNodeFn = Callable[[tuple[RenderBuffer, ...]], RenderBuffer]


@dataclass(frozen=True, slots=True)
class RenderNode:
    """One deterministic render stage with explicitly declared upstream nodes."""

    name: str
    process: RenderNodeFn
    dependencies: tuple[str, ...] = ()
    mask: RenderMask | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("render node name must be a non-empty string")
        if not callable(self.process):
            raise TypeError("render node process must be callable")
        if not isinstance(self.dependencies, tuple):
            raise TypeError("render node dependencies must be a tuple")
        if any(not isinstance(name, str) or not name.strip() for name in self.dependencies):
            raise ValueError("render node dependency names must be non-empty strings")
        if len(set(self.dependencies)) != len(self.dependencies):
            raise ValueError("render node dependencies must be unique")
        if self.mask is not None and not isinstance(self.mask, RenderMask):
            raise TypeError("render node mask must be a RenderMask")
        if self.mask is not None and len(self.dependencies) > 1:
            raise ValueError("masked render nodes must be unary")

    def _validate_mask_source(self, source: RenderBuffer) -> None:
        if self.mask is not None and self.mask.shape != source.shape[:2]:
            raise ValueError("render mask dimensions must match RenderBuffer dimensions")

    def _apply_mask(
        self,
        source: RenderBuffer,
        processed: RenderBuffer,
    ) -> RenderBuffer:
        if self.mask is None:
            return processed
        return SelectiveRegionEffect(lambda _: processed, self.mask)((source,))


class RenderGraph:
    """Validated deterministic DAG that transforms an initial RenderBuffer."""

    def __init__(self, nodes: Iterable[RenderNode]) -> None:
        node_list = tuple(nodes)
        if not node_list:
            raise ValueError("render graph requires at least one node")
        if any(not isinstance(node, RenderNode) for node in node_list):
            raise TypeError("render graph nodes must be RenderNode values")

        names = [node.name for node in node_list]
        if len(set(names)) != len(names):
            raise ValueError("render graph contains duplicate node names")

        by_name = {node.name: node for node in node_list}
        for node in node_list:
            if node.name in node.dependencies:
                raise ValueError(f"render node {node.name!r} cannot depend on itself")
            missing = [name for name in node.dependencies if name not in by_name]
            if missing:
                raise ValueError(
                    f"render node {node.name!r} has missing dependencies: {missing}"
                )

        order = self._topological_order(node_list)
        terminals = tuple(
            node.name
            for node in node_list
            if not any(node.name in other.dependencies for other in node_list)
        )
        if len(terminals) != 1:
            raise ValueError("render graph must have exactly one terminal node")

        self._nodes = by_name
        self._execution_order = order
        self._terminal = terminals[0]

    @staticmethod
    def _topological_order(nodes: tuple[RenderNode, ...]) -> tuple[str, ...]:
        indegree = {node.name: len(node.dependencies) for node in nodes}
        dependants: dict[str, list[str]] = {node.name: [] for node in nodes}
        declaration_index = {node.name: index for index, node in enumerate(nodes)}

        for node in nodes:
            for dependency in node.dependencies:
                dependants[dependency].append(node.name)

        ready = [node.name for node in nodes if indegree[node.name] == 0]
        order: list[str] = []
        while ready:
            ready.sort(key=declaration_index.__getitem__)
            current = ready.pop(0)
            order.append(current)
            for dependant in dependants[current]:
                indegree[dependant] -= 1
                if indegree[dependant] == 0:
                    ready.append(dependant)

        if len(order) != len(nodes):
            raise ValueError("render graph contains a dependency cycle")
        return tuple(order)

    @property
    def execution_order(self) -> tuple[str, ...]:
        """Return the deterministic node execution order."""
        return self._execution_order

    @property
    def terminal_node(self) -> str:
        """Return the single terminal node name."""
        return self._terminal

    def execute(self, initial: RenderBuffer) -> RenderBuffer:
        """Execute the graph from one canonical initial RenderBuffer."""
        if not isinstance(initial, RenderBuffer):
            raise TypeError("initial must be a RenderBuffer")

        outputs: dict[str, RenderBuffer] = {}
        for name in self._execution_order:
            node = self._nodes[name]
            if node.dependencies:
                inputs = tuple(outputs[dependency] for dependency in node.dependencies)
            else:
                inputs = (initial.copy(),)

            node._validate_mask_source(inputs[0])
            result = node.process(inputs)
            if not isinstance(result, RenderBuffer):
                raise TypeError(f"render node {name!r} must return a RenderBuffer")
            if any(result is input_buffer for input_buffer in inputs):
                raise ValueError(f"render node {name!r} must return a new RenderBuffer")
            if result.shape != initial.shape:
                raise ValueError(f"render node {name!r} changed render dimensions")

            outputs[name] = node._apply_mask(inputs[0], result)

        return outputs[self._terminal]
