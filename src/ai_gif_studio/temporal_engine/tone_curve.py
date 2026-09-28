from __future__ import annotations

import numpy as np

from ai_gif_studio.temporal_engine.render_buffer import RenderBuffer


class ToneCurve:
    """Immutable piecewise-linear color grading curve."""

    def __init__(self, points: np.ndarray) -> None:
        values = np.asarray(points)
        if values.ndim != 2 or values.shape[1] != 2 or values.shape[0] < 2:
            raise ValueError("tone curve points must have shape (N, 2) with N >= 2")
        if not np.issubdtype(values.dtype, np.floating):
            raise TypeError("tone curve points must be floating point")
        if not np.isfinite(values).all():
            raise ValueError("tone curve points must be finite")
        if np.any(np.diff(values[:, 0]) <= 0.0):
            raise ValueError("tone curve x coordinates must be strictly increasing")

        owned = np.array(values, dtype=np.float64, copy=True)
        owned.setflags(write=False)
        self._points = owned

    @classmethod
    def from_points(cls, points: tuple[tuple[float, float], ...] | np.ndarray) -> ToneCurve:
        """Construct a curve from ordered x/y control points."""
        return cls(np.asarray(points))

    @property
    def points(self) -> np.ndarray:
        """Return immutable owned control points."""
        return self._points

    def evaluate(self, values: np.ndarray) -> np.ndarray:
        """Evaluate with piecewise-linear interpolation and endpoint extrapolation."""
        values = np.asarray(values, dtype=np.float64)
        x = self._points[:, 0]
        y = self._points[:, 1]

        indices = np.searchsorted(x, values, side="right") - 1
        indices = np.clip(indices, 0, len(x) - 2)

        x0 = x[indices]
        x1 = x[indices + 1]
        y0 = y[indices]
        y1 = y[indices + 1]
        slope = (y1 - y0) / (x1 - x0)
        return y0 + (values - x0) * slope


class ToneCurveEffect:
    """Deterministic channel-wise tone curves over canonical linear RGB."""

    def __init__(
        self,
        red: ToneCurve,
        green: ToneCurve | None = None,
        blue: ToneCurve | None = None,
    ) -> None:
        if not isinstance(red, ToneCurve):
            raise TypeError("red must be a ToneCurve")
        if green is None and blue is not None:
            raise ValueError("green must be provided when blue is provided")
        if green is None:
            green = red
        if blue is None:
            blue = green
        if not isinstance(green, ToneCurve) or not isinstance(blue, ToneCurve):
            raise TypeError("channel curves must be ToneCurve values")

        self._curves = (red, green, blue)

    @property
    def curves(self) -> tuple[ToneCurve, ToneCurve, ToneCurve]:
        """Return the immutable channel curve tuple."""
        return self._curves

    def __call__(self, inputs: tuple[RenderBuffer, ...]) -> RenderBuffer:
        if len(inputs) != 1:
            raise ValueError("ToneCurveEffect requires exactly one RenderBuffer input")
        source = inputs[0]
        if not isinstance(source, RenderBuffer):
            raise TypeError("ToneCurveEffect input must be a RenderBuffer")

        data = source.data.copy()
        for channel, curve in enumerate(self._curves):
            data[..., channel] = curve.evaluate(data[..., channel])
        return RenderBuffer.from_linear_rgba(data)
