""""Deterministic straight-alpha compositor for canonical RenderBuffer layers."""
from __future__ import annotations

from collections.abc import Iterable

import numpy as np

from .render_buffer import RenderBuffer


def composite_over(destination: RenderBuffer, source: RenderBuffer) -> RenderBuffer:
    """Composite source over destination using straight-alpha Porter-Duff over.

    Both buffers must have identical dimensions. Inputs are never mutated and
    the returned buffer owns independent float32 linear RGBA storage.
    """
    _validate_pair(destination, source)

    dst = destination.data
    src = source.data
    src_alpha = src[..., 3:4]
    dst_alpha = dst[..., 3:4]
    inverse_src_alpha = 1.0 - src_alpha

    premultiplied_rgb = (
        src[..., :3] * src_alpha
        + dst[..., :3] * dst_alpha * inverse_src_alpha
    )
    alpha = src_alpha + dst_alpha * inverse_src_alpha
    rgb = np.divide(
        premultiplied_rgb,
        alpha,
        out=np.zeros_like(premultiplied_rgb),
        where=alpha > 0.0,
    )
    return RenderBuffer.from_linear_rgba(
        np.concatenate([rgb, alpha], axis=-1).astype(np.float32)
    )


def composite_layers(layers: Iterable[RenderBuffer]) -> RenderBuffer:
    """Composite an ordered layer sequence from back to front.

    An empty sequence is rejected because a compositor output requires an
    explicit target size and there is no canonical size to infer otherwise.
    """
    iterator = iter(layers)
    try:
        result = next(iterator).copy()
    except StopIteration as exc:
        raise ValueError("at least one RenderBuffer layer is required") from exc

    for layer in iterator:
        result = composite_over(result, layer)
    return result


def _validate_pair(destination: RenderBuffer, source: RenderBuffer) -> None:
    if not isinstance(destination, RenderBuffer):
        raise TypeError("destination must be a RenderBuffer")
    if not isinstance(source, RenderBuffer):
        raise TypeError("source must be a RenderBuffer")
    if destination.shape != source.shape:
        raise ValueError("source and destination RenderBuffer shapes must match")
