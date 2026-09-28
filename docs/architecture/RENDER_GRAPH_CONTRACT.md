# Phase 4.4 — Render Graph Contract

## Purpose
The Render Graph is the orchestration boundary between canonical RenderBuffer storage and future render stages such as PBR, masks, effects, color-management boundaries, and GPU backends.

This phase defines orchestration only. It does not rewrite the existing PBR implementation.

## Contract
A render graph is an ordered, acyclic collection of named render nodes.

Each node:
- has a unique non-empty string name;
- declares zero or more upstream node names;
- receives exactly one canonical RenderBuffer value when executed;
- returns a new canonical RenderBuffer;
- must not mutate its input;
- must preserve the input dimensions unless the graph contract is explicitly extended for resampling;
- must be deterministic for identical input and node configuration.

The graph:
- accepts one initial RenderBuffer;
- validates node names and dependencies before execution;
- rejects duplicate node names;
- rejects missing dependencies;
- rejects self-dependencies and dependency cycles;
- executes each node at most once;
- executes dependencies before dependants;
- produces the terminal node output;
- rejects graphs with no nodes;
- rejects graphs with multiple terminal nodes for the single-output API;
- rejects a node that returns anything other than RenderBuffer;
- rejects a node that changes the canonical render dimensions;
- never mutates the caller's initial buffer.


A node with multiple dependencies receives their outputs in the exact dependency declaration order. This provides deterministic fan-in for future compositor/effect stages without introducing implicit global state.

## Execution model
The first implementation intentionally exposes a single-output graph:

initial RenderBuffer -> node graph -> terminal RenderBuffer

Multiple inputs/outputs, resource handles, GPU command scheduling, temporal state, and graph-wide metadata are deferred until a concrete requirement exists.

A node may capture immutable scene/PBR configuration in its callable. This allows existing PBR/multi-light functionality to be integrated later without changing the PBR math or forcing scene-specific data into RenderBuffer.

## Determinism
The graph must derive execution order solely from declared dependencies. When several nodes are independently ready, their order must be stable and deterministic from graph declaration order.

## Error semantics
Invalid graph topology is rejected before any node executes. Runtime node failures propagate without being converted into generic errors. A node returning an invalid output raises a contract error identifying the node.

## Non-goals
This phase does not introduce:
- a PBR rewrite;
- GPU execution;
- parallel scheduling;
- mutable graph state;
- automatic graph optimization;
- implicit color-space conversion;
- resampling;
- multiple render targets.

These are separate architectural decisions.