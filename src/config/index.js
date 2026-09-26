/**
 * Central, versioned render configuration.
 *
 * Processing engines must read their render limits and capabilities from this
 * module rather than embedding values such as canvas dimensions or FPS.
 */
export const CONFIG_SCHEMA_VERSION = 1;

const BACKGROUND_MODES = ['solid', 'gradient', 'blurred', 'mirrored'];
const FRAME_GEOMETRIES = ['rectangle', 'rounded-rectangle', 'circle', 'ellipse', 'portrait', 'landscape'];
const FRAME_ANIMATION_PATHS = ['none', 'fade', 'zoom-in', 'zoom-out', 'pan-left', 'pan-right', 'pan-up', 'pan-down', 'orbit'];
const FPS_FALLBACK_LADDER = [30, 27, 24, 20, 18, 15];

export const DEFAULT_RENDER_CONFIGURATION = deepFreeze({
  schemaVersion: CONFIG_SCHEMA_VERSION,
  canvas: { width: 320, height: 320 },
  durationSeconds: 6,
  maximumOutputBytes: 2_400_000,
  fps: { preferred: 30, fallbackLadder: FPS_FALLBACK_LADDER },
  supported: {
    backgroundModes: BACKGROUND_MODES,
    frameGeometries: FRAME_GEOMETRIES,
    frameAnimationPaths: FRAME_ANIMATION_PATHS,
  },
  foreground: { scale: { minimum: 0.5, maximum: 1 } },
  quality: {
    presets: {
      high: { crf: 18, effort: 8 },
      balanced: { crf: 23, effort: 6 },
      compact: { crf: 28, effort: 4 },
    },
    defaultPreset: 'balanced',
  },
  palette: { minimumColors: 32, maximumColors: 256, defaultColors: 256 },
  dithering: { modes: ['none', 'floyd-steinberg', 'sierra'], defaultMode: 'floyd-steinberg' },
  crop: { modes: ['contain', 'cover', 'stretch'], defaultMode: 'cover', allowFocalPoint: true },
  composition: {
    alignments: ['center', 'top', 'bottom', 'left', 'right'],
    defaultAlignment: 'center',
    allowSafeArea: true,
    safeAreaPercent: 0.05,
  },
});

/** A JSON-schema-like document for consumers that need to inspect the contract. */
export const RENDER_CONFIGURATION_SCHEMA = deepFreeze({
  $id: 'ai-gif-studio/render-configuration',
  version: CONFIG_SCHEMA_VERSION,
  type: 'object',
  required: ['schemaVersion', 'canvas', 'durationSeconds', 'maximumOutputBytes', 'fps'],
  properties: {
    schemaVersion: { const: CONFIG_SCHEMA_VERSION },
    canvas: { type: 'object', required: ['width', 'height'] },
    durationSeconds: { type: 'number', exclusiveMinimum: 0 },
    maximumOutputBytes: { type: 'integer', minimum: 1 },
    fps: { type: 'object', required: ['preferred', 'fallbackLadder'] },
  },
});

/**
 * Returns a validated configuration. Legacy flat keys are upgraded before
 * merging, preserving callers that previously supplied width, height, duration,
 * maxOutputBytes, preferredFps, or fpsFallbackLadder at the root.
 */
export function createRenderConfiguration(overrides = {}) {
  const migrated = migrateLegacyConfiguration(overrides);
  const configuration = merge(DEFAULT_RENDER_CONFIGURATION, migrated);
  validateRenderConfiguration(configuration);
  return deepFreeze(configuration);
}

/** Upgrade supported pre-schema (flat) configuration keys to schema version 1. */
export function migrateLegacyConfiguration(input = {}) {
  if (!isPlainObject(input)) throw new TypeError('Render configuration must be an object.');
  const migrated = { ...input };
  const legacyCanvas = {};
  if ('width' in migrated) { legacyCanvas.width = migrated.width; delete migrated.width; }
  if ('height' in migrated) { legacyCanvas.height = migrated.height; delete migrated.height; }
  if (Object.keys(legacyCanvas).length) migrated.canvas = { ...legacyCanvas, ...migrated.canvas };
  const aliases = {
    duration: 'durationSeconds', maxOutputBytes: 'maximumOutputBytes',
    preferredFps: 'fps.preferred', fpsFallbackLadder: 'fps.fallbackLadder',
  };
  for (const [legacyKey, path] of Object.entries(aliases)) {
    if (!(legacyKey in migrated)) continue;
    const value = migrated[legacyKey]; delete migrated[legacyKey];
    if (path.startsWith('fps.')) migrated.fps = { [path.slice(4)]: value, ...migrated.fps };
    else if (!(path in migrated)) migrated[path] = value;
  }
  if (migrated.schemaVersion === undefined) migrated.schemaVersion = CONFIG_SCHEMA_VERSION;
  return migrated;
}

/** Throws TypeError with all configuration errors, or returns the configuration. */
export function validateRenderConfiguration(configuration) {
  const errors = [];
  const value = configuration;
  if (!isPlainObject(value)) errors.push('configuration must be an object');
  if (value?.schemaVersion !== CONFIG_SCHEMA_VERSION) errors.push(`schemaVersion must be ${CONFIG_SCHEMA_VERSION}`);
  positiveInteger(value?.canvas?.width, 'canvas.width', errors);
  positiveInteger(value?.canvas?.height, 'canvas.height', errors);
  positiveNumber(value?.durationSeconds, 'durationSeconds', errors);
  positiveInteger(value?.maximumOutputBytes, 'maximumOutputBytes', errors);
  positiveNumber(value?.fps?.preferred, 'fps.preferred', errors);
  const ladder = value?.fps?.fallbackLadder;
  if (!Array.isArray(ladder) || ladder.length === 0 || ladder.some((fps) => !Number.isFinite(fps) || fps <= 0)) errors.push('fps.fallbackLadder must contain positive numbers');
  else {
    if (ladder[0] !== value.fps.preferred) errors.push('fps.fallbackLadder must start with fps.preferred');
    if (ladder.some((fps, index) => index > 0 && fps >= ladder[index - 1])) errors.push('fps.fallbackLadder must be strictly descending');
  }
  enumList(value?.supported?.backgroundModes, BACKGROUND_MODES, 'supported.backgroundModes', errors);
  enumList(value?.supported?.frameGeometries, FRAME_GEOMETRIES, 'supported.frameGeometries', errors);
  enumList(value?.supported?.frameAnimationPaths, FRAME_ANIMATION_PATHS, 'supported.frameAnimationPaths', errors);
  const scale = value?.foreground?.scale;
  positiveNumber(scale?.minimum, 'foreground.scale.minimum', errors);
  positiveNumber(scale?.maximum, 'foreground.scale.maximum', errors);
  if (Number.isFinite(scale?.minimum) && Number.isFinite(scale?.maximum) && scale.minimum > scale.maximum) errors.push('foreground.scale.minimum must not exceed foreground.scale.maximum');
  const quality = value?.quality;
  if (!isPlainObject(quality?.presets) || Object.keys(quality.presets).length === 0) errors.push('quality.presets must be a non-empty object');
  else {
    for (const [name, preset] of Object.entries(quality.presets)) {
      if (!Number.isInteger(preset?.crf) || preset.crf < 0 || preset.crf > 63) errors.push(`quality.presets.${name}.crf must be an integer between 0 and 63`);
      positiveInteger(preset?.effort, `quality.presets.${name}.effort`, errors);
    }
  }
  if (!quality?.presets?.[quality?.defaultPreset]) errors.push('quality.defaultPreset must name a configured quality preset');
  const palette = value?.palette;
  positiveInteger(palette?.minimumColors, 'palette.minimumColors', errors);
  positiveInteger(palette?.maximumColors, 'palette.maximumColors', errors);
  positiveInteger(palette?.defaultColors, 'palette.defaultColors', errors);
  if (palette && (palette.minimumColors > palette.maximumColors || palette.defaultColors < palette.minimumColors || palette.defaultColors > palette.maximumColors)) errors.push('palette defaultColors must be within its configured range');
  stringList(value?.dithering?.modes, 'dithering.modes', errors);
  if (!value?.dithering?.modes?.includes(value?.dithering?.defaultMode)) errors.push('dithering.defaultMode must be listed in dithering.modes');
  stringList(value?.crop?.modes, 'crop.modes', errors);
  if (!value?.crop?.modes?.includes(value?.crop?.defaultMode)) errors.push('crop.defaultMode must be listed in crop.modes');
  if (typeof value?.crop?.allowFocalPoint !== 'boolean') errors.push('crop.allowFocalPoint must be a boolean');
  stringList(value?.composition?.alignments, 'composition.alignments', errors);
  if (!value?.composition?.alignments?.includes(value?.composition?.defaultAlignment)) errors.push('composition.defaultAlignment must be listed in composition.alignments');
  if (typeof value?.composition?.allowSafeArea !== 'boolean') errors.push('composition.allowSafeArea must be a boolean');
  if (!Number.isFinite(value?.composition?.safeAreaPercent) || value.composition.safeAreaPercent < 0 || value.composition.safeAreaPercent >= 0.5) errors.push('composition.safeAreaPercent must be between 0 (inclusive) and 0.5 (exclusive)');
  if (errors.length) throw new TypeError(`Invalid render configuration: ${errors.join('; ')}.`);
  return configuration;
}

function enumList(values, allowed, name, errors) {
  if (!Array.isArray(values) || values.length === 0 || values.some((value) => !allowed.includes(value))) errors.push(`${name} must be a non-empty subset of: ${allowed.join(', ')}`);
}
function stringList(values, name, errors) { if (!Array.isArray(values) || values.length === 0 || values.some((value) => typeof value !== 'string' || value.length === 0)) errors.push(`${name} must be a non-empty array of strings`); }
function positiveInteger(value, name, errors) { if (!Number.isInteger(value) || value <= 0) errors.push(`${name} must be a positive integer`); }
function positiveNumber(value, name, errors) { if (!Number.isFinite(value) || value <= 0) errors.push(`${name} must be a positive number`); }
function isPlainObject(value) { return value !== null && typeof value === 'object' && !Array.isArray(value); }
function merge(base, override) {
  if (Array.isArray(base)) return override === undefined ? [...base] : [...override];
  if (!isPlainObject(base)) return override === undefined ? base : override;
  const result = {};
  for (const key of new Set([...Object.keys(base), ...Object.keys(override ?? {})])) {
    result[key] = key in (override ?? {}) ? merge(base[key], override[key]) : merge(base[key]);
  }
  return result;
}
function deepFreeze(value) {
  if (value && typeof value === 'object' && !Object.isFrozen(value)) {
    Object.values(value).forEach(deepFreeze); Object.freeze(value);
  }
  return value;
}
