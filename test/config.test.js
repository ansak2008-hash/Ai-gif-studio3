import test from 'node:test';
import assert from 'node:assert/strict';
import { createRenderConfiguration, DEFAULT_RENDER_CONFIGURATION, validateRenderConfiguration } from '../src/config/index.js';

test('uses the versioned central render defaults', () => {
  const config = createRenderConfiguration();
  assert.equal(config.schemaVersion, 1);
  assert.deepEqual(config.canvas, { width: 320, height: 320 });
  assert.equal(config.durationSeconds, 6);
  assert.equal(config.maximumOutputBytes, 2_400_000);
  assert.deepEqual(config.fps.fallbackLadder, [30, 27, 24, 20, 18, 15]);
  assert.deepEqual(config.supported.backgroundModes, ['solid', 'gradient', 'blurred', 'mirrored']);
  assert.ok(Object.isFrozen(config));
});

test('migrates legacy flat options while allowing future canvas changes centrally', () => {
  const config = createRenderConfiguration({ width: 640, height: 480, duration: 8, preferredFps: 24, fpsFallbackLadder: [24, 20, 15] });
  assert.deepEqual(config.canvas, { width: 640, height: 480 });
  assert.equal(config.durationSeconds, 8);
  assert.deepEqual(config.fps, { preferred: 24, fallbackLadder: [24, 20, 15] });
});

test('rejects invalid cross-field settings', () => {
  assert.throws(() => createRenderConfiguration({ fps: { preferred: 30, fallbackLadder: [30, 30] } }), /strictly descending/);
  assert.throws(() => validateRenderConfiguration({ ...DEFAULT_RENDER_CONFIGURATION, palette: { minimumColors: 64, maximumColors: 32, defaultColors: 32 } }), /palette/);
});
