/** Public, dependency-free schemas for the composition/layout boundary. */
export const COMPOSITION_CANVAS_SIZE = 320 as const;

export type CompositionShape = "circle" | "rounded-rect" | "rect";
export type CompositionMode = "auto" | "cover" | "contain";
export type SourceAspect = "16:9" | "9:16" | "1:1" | "4:3" | "4:5" | "arbitrary";

export interface Point { x: number; y: number }
export interface Bounds { x: number; y: number; width: number; height: number }

/** Normalized source coordinates, where 0,0 is top-left and 1,1 is bottom-right. */
export interface FocusPoint extends Point {}

export interface CompositionInput {
  /** Pixel dimensions from decoded video metadata; never inferred from CSS dimensions. */
  source: { width: number; height: number };
  /** Optional subject focus, from tracking/detection. Defaults to optical centre. */
  focus?: FocusPoint;
  /** The inner surface used to present media. */
  shape?: CompositionShape;
  /** `auto` crops only when a contained source would look undersized or letterboxed. */
  mode?: CompositionMode;
  /** 0..1: compact favors a larger foreground, editorial creates more breathing room. */
  density?: number;
  /** Optional normalized visual weight used to nudge the design away from the subject. */
  preferredAnchor?: "center" | "top" | "bottom";
  /** Required only for rounded-rect; the radius is clamped to half the short side. */
  cornerRadius?: number;
}

export interface SourceCrop {
  /** Crop rectangle in original source pixels. */
  sourceBounds: Bounds;
  /** Normalized focus actually retained after crop clamping. */
  retainedFocus: FocusPoint;
}

export interface CompositionLayout {
  canvas: { width: 320; height: 320 };
  sourceAspect: SourceAspect;
  /** Bounds of the internal design surface. Frame Engine must use this, never `canvas`. */
  foregroundBounds: Bounds;
  /** The visible media region. Equal to foregroundBounds for cover/circle. */
  mediaBounds: Bounds;
  /** Uniform media scale, relative to the un-cropped source. This prevents stretching. */
  mediaScale: number;
  crop: SourceCrop | null;
  clip: { shape: CompositionShape; bounds: Bounds; cornerRadius: number };
  /** Space outside foregroundBounds, reserved for captions, frames, and visual breathing room. */
  breathingRoom: { top: number; right: number; bottom: number; left: number };
}

export function assertCompositionInput(input: CompositionInput): void {
  const { source } = input;
  if (!Number.isFinite(source?.width) || !Number.isFinite(source?.height) || source.width <= 0 || source.height <= 0) {
    throw new TypeError("source.width and source.height must be finite positive numbers");
  }
  if (input.density !== undefined && (!Number.isFinite(input.density) || input.density < 0 || input.density > 1)) {
    throw new RangeError("density must be between 0 and 1");
  }
  if (input.focus && (!Number.isFinite(input.focus.x) || !Number.isFinite(input.focus.y))) {
    throw new TypeError("focus coordinates must be finite numbers");
  }
}
