"""Explicit adapter from immutable layer state to compositor-ready layers."""
from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from ai_gif_studio.domain.layer_state import LayerStack
from ai_gif_studio.temporal_engine.blend import BlendMode
from ai_gif_studio.temporal_engine.compositor import BlendLayer
from ai_gif_studio.temporal_engine.render_buffer import RenderBuffer
from ai_gif_studio.temporal_engine.mask_processing import process_mask
from ai_gif_studio.temporal_engine.render_mask import RenderMask


def bind_layer_stack(
    stack: LayerStack,
    sources: Mapping[UUID, RenderBuffer],
    *,
    masks: Mapping[UUID, RenderMask] | None = None,
) -> tuple[BlendLayer, ...]:
    """Translate visible domain layers into deterministic compositor inputs.

    The caller owns source buffers and the source mapping. This adapter never
    mutates or takes ownership of those pixel buffers.
    """
    if not isinstance(stack, LayerStack):
        raise TypeError("stack must be a LayerStack")
    if not isinstance(sources, Mapping):
        raise TypeError("sources must be a mapping")
    if masks is not None and not isinstance(masks, Mapping):
        raise TypeError("masks must be a mapping")

    visible_layers = tuple(layer for layer in stack.layers if layer.visible)
    resolved: list[tuple[object, RenderBuffer]] = []
    for layer in visible_layers:
        try:
            source = sources[layer.source_asset_id]
        except KeyError as exc:
            raise KeyError(f"source_asset_id not found: {layer.source_asset_id}") from exc
        if not isinstance(source, RenderBuffer):
            raise TypeError("source mapping values must be RenderBuffer instances")
        resolved.append((layer, source))

    bindings: list[BlendLayer] = []
    for layer, source in resolved:
        if layer.mask is not None:
            if masks is None:
                raise ValueError("mask resolution mapping is required for masked layers")
            try:
                source_mask = masks[layer.mask.source_asset_id]
            except KeyError as exc:
                raise KeyError(
                    f"mask source_asset_id not found: {layer.mask.source_asset_id}"
                ) from exc
            if not isinstance(source_mask, RenderMask):
                raise TypeError("mask mapping values must be RenderMask instances")
            if source_mask.shape != (source.height, source.width):
                raise ValueError("mask dimensions must match source RenderBuffer")
            resolved_mask = process_mask(source_mask, layer.mask)
            if layer.opacity != 1.0:
                resolved_mask = RenderMask.from_array(
                    (resolved_mask.data * layer.opacity).astype(np.float32)
                )
            mask = resolved_mask
        else:
            mask = (
                None
                if layer.opacity == 1.0
                else RenderMask.allocate(source.width, source.height, value=layer.opacity)
            )
        bindings.append(
            BlendLayer(source=source, mode=BlendMode(layer.blend_mode.value), mask=mask)
        )
    return tuple(bindings)
