from dataclasses import dataclass

import numpy as np


def _normalize(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    if n < 1e-12:
        raise ValueError("cannot normalize a near-zero vector")
    return v / n


@dataclass(frozen=True)
class CameraState:
    position: tuple[float, float, float]
    target: tuple[float, float, float]
    up: tuple[float, float, float]
    fov_y_deg: float
    aspect: float
    near: float = 0.01
    far: float = 10000.0
    roll_deg: float = 0.0

    def __post_init__(self) -> None:
        if not 0.0 < self.fov_y_deg < 180.0:
            raise ValueError("fov_y_deg must be in (0, 180)")
        if self.aspect <= 0.0:
            raise ValueError("aspect must be positive")
        if self.near <= 0.0 or self.far <= self.near:
            raise ValueError("invalid near/far clip planes")

    def view_matrix(self) -> np.ndarray:
        eye = np.asarray(self.position, dtype=np.float64)
        target = np.asarray(self.target, dtype=np.float64)
        up = _normalize(np.asarray(self.up, dtype=np.float64))
        z_axis = _normalize(eye - target)
        x_axis = _normalize(np.cross(up, z_axis))
        y_axis = np.cross(z_axis, x_axis)
        if self.roll_deg:
            r = np.deg2rad(self.roll_deg)
            c, s = float(np.cos(r)), float(np.sin(r))
            x_axis, y_axis = c * x_axis + s * y_axis, -s * x_axis + c * y_axis
        return np.array(
            [
                [*x_axis, -float(np.dot(x_axis, eye))],
                [*y_axis, -float(np.dot(y_axis, eye))],
                [*z_axis, -float(np.dot(z_axis, eye))],
                [0.0, 0.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        )

    def projection_matrix(self) -> np.ndarray:
        f = 1.0 / np.tan(np.deg2rad(self.fov_y_deg) * 0.5)
        n, fa = self.near, self.far
        return np.array(
            [
                [f / self.aspect, 0.0, 0.0, 0.0],
                [0.0, f, 0.0, 0.0],
                [0.0, 0.0, (fa + n) / (n - fa), 2.0 * fa * n / (n - fa)],
                [0.0, 0.0, -1.0, 0.0],
            ],
            dtype=np.float64,
        )

    def view_projection(self) -> np.ndarray:
        return self.projection_matrix() @ self.view_matrix()


@dataclass(frozen=True)
class CameraModel:
    state: CameraState

    @property
    def view_matrix(self) -> np.ndarray:
        return self.state.view_matrix()

    @property
    def projection_matrix(self) -> np.ndarray:
        return self.state.projection_matrix()

    @property
    def view_projection(self) -> np.ndarray:
        return self.state.view_projection()


def project_points(
    view_projection: np.ndarray,
    points_world: np.ndarray,
    viewport: tuple[int, int],
) -> tuple[np.ndarray, np.ndarray]:
    points = np.asarray(points_world, dtype=np.float64)
    matrix = np.asarray(view_projection, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3 or matrix.shape != (4, 4):
        raise ValueError("invalid projection inputs")
    width, height = viewport
    homogeneous = np.concatenate([points, np.ones((len(points), 1))], axis=1)
    clip = (matrix @ homogeneous.T).T
    w = clip[:, 3]
    valid = w > 1e-9
    ndc = np.zeros((len(points), 3), dtype=np.float64)
    ndc[valid] = clip[valid, :3] / w[valid, None]
    screen = np.empty((len(points), 2), dtype=np.float64)
    screen[:, 0] = (ndc[:, 0] + 1.0) * 0.5 * width
    screen[:, 1] = (1.0 - ndc[:, 1]) * 0.5 * height
    return screen, valid
