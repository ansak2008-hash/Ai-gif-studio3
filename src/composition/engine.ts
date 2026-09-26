import {
  assertCompositionInput, COMPOSITION_CANVAS_SIZE, type Bounds, type CompositionInput,
  type CompositionLayout, type FocusPoint, type SourceAspect,
} from "./schema.js";

const CANVAS = COMPOSITION_CANVAS_SIZE;
const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));
const round = (value: number) => Math.round(value * 100) / 100;
const equal = (a: number, b: number) => Math.abs(a - b) < 0.025;

function sourceAspect(width: number, height: number): SourceAspect {
  const ratio = width / height;
  if (equal(ratio, 16 / 9)) return "16:9";
  if (equal(ratio, 9 / 16)) return "9:16";
  if (equal(ratio, 1)) return "1:1";
  if (equal(ratio, 4 / 3)) return "4:3";
  if (equal(ratio, 4 / 5)) return "4:5";
  return "arbitrary";
}

/**
 * Selects an editorial surface rather than blindly reusing source dimensions.
 * Extreme source ratios are softly normalized, avoiding a tiny thin video in a square output.
 */
function designRatio(sourceRatio: number, shape: CompositionInput["shape"]): number {
  if (shape === "circle") return 1;
  if (sourceRatio >= 1.35) return 1.08; // landscape becomes a near-square hero crop
  if (sourceRatio <= 0.74) return 0.82; // portrait remains intentionally portrait, without touching canvas edges
  return clamp(sourceRatio, 0.88, 1.12);
}

function cropForCover(source: CompositionInput["source"], targetRatio: number, focus: FocusPoint): CompositionLayout["crop"] {
  const sourceRatio = source.width / source.height;
  let cropWidth: number;
  let cropHeight: number;
  if (sourceRatio > targetRatio) {
    cropHeight = source.height;
    cropWidth = cropHeight * targetRatio;
  } else {
    cropWidth = source.width;
    cropHeight = cropWidth / targetRatio;
  }
  const desiredX = focus.x * source.width - cropWidth / 2;
  const desiredY = focus.y * source.height - cropHeight / 2;
  const x = clamp(desiredX, 0, source.width - cropWidth);
  const y = clamp(desiredY, 0, source.height - cropHeight);
  return {
    sourceBounds: { x: round(x), y: round(y), width: round(cropWidth), height: round(cropHeight) },
    retainedFocus: { x: round((focus.x * source.width - x) / cropWidth), y: round((focus.y * source.height - y) / cropHeight) },
  };
}

function boundsFor(ratio: number, scale: number, anchor: CompositionInput["preferredAnchor"]): Bounds {
  const longSide = CANVAS * scale;
  const width = ratio >= 1 ? longSide : longSide * ratio;
  const height = ratio >= 1 ? longSide / ratio : longSide;
  const x = (CANVAS - width) / 2;
  // A small anchor movement retains intentional breathing room and never touches an edge.
  const naturalY = (CANVAS - height) / 2;
  const nudge = (CANVAS - height) * 0.16;
  const y = anchor === "top" ? naturalY - nudge : anchor === "bottom" ? naturalY + nudge : naturalY;
  return { x: round(x), y: round(y), width: round(width), height: round(height) };
}

/** Creates a 320×320 composition plan; drawing/rendering remains the caller's responsibility. */
export function createComposition(input: CompositionInput): CompositionLayout {
  assertCompositionInput(input);
  const shape = input.shape ?? "rounded-rect";
  const mode = input.mode ?? "auto";
  const focus = { x: clamp(input.focus?.x ?? 0.5, 0, 1), y: clamp(input.focus?.y ?? 0.5, 0, 1) };
  const sourceRatio = input.source.width / input.source.height;
  const ratio = designRatio(sourceRatio, shape);
  // 70–95% is an explicit creative constraint, not an incidental result of fit math.
  const density = input.density ?? 0.52;
  const foregroundScale = clamp(0.7 + density * 0.25, 0.7, 0.95);
  const foregroundBounds = boundsFor(ratio, foregroundScale, input.preferredAnchor ?? "center");
  const needsCrop = mode === "cover" || (mode === "auto" && Math.abs(Math.log(sourceRatio / ratio)) > 0.09) || shape === "circle";
  const crop = needsCrop ? cropForCover(input.source, ratio, focus) : null;
  const mediaScale = crop
    ? foregroundBounds.width / crop.sourceBounds.width
    : Math.min(foregroundBounds.width / input.source.width, foregroundBounds.height / input.source.height);
  const mediaWidth = input.source.width * mediaScale;
  const mediaHeight = input.source.height * mediaScale;
  const mediaBounds = crop
    ? foregroundBounds
    : { x: round(foregroundBounds.x + (foregroundBounds.width - mediaWidth) / 2), y: round(foregroundBounds.y + (foregroundBounds.height - mediaHeight) / 2), width: round(mediaWidth), height: round(mediaHeight) };
  const cornerRadius = shape === "rounded-rect"
    ? round(clamp(input.cornerRadius ?? Math.min(foregroundBounds.width, foregroundBounds.height) * 0.1, 0, Math.min(foregroundBounds.width, foregroundBounds.height) / 2))
    : shape === "circle" ? round(Math.min(foregroundBounds.width, foregroundBounds.height) / 2) : 0;
  return {
    canvas: { width: CANVAS, height: CANVAS }, sourceAspect: sourceAspect(input.source.width, input.source.height),
    foregroundBounds, mediaBounds, mediaScale: round(mediaScale), crop,
    clip: { shape, bounds: foregroundBounds, cornerRadius },
    breathingRoom: {
      top: round(foregroundBounds.y), right: round(CANVAS - foregroundBounds.x - foregroundBounds.width),
      bottom: round(CANVAS - foregroundBounds.y - foregroundBounds.height), left: round(foregroundBounds.x),
    },
  };
}
