import assert from "node:assert/strict";
import test from "node:test";
import { createComposition } from "./engine.js";

test("keeps a 16:9 video proportional and crops it into an internal foreground", () => {
  const layout = createComposition({ source: { width: 1920, height: 1080 }, density: 0.5 });
  assert.equal(layout.sourceAspect, "16:9");
  assert.ok(layout.crop);
  assert.ok(layout.foregroundBounds.width < 320);
  assert.ok(layout.foregroundBounds.height < 320);
  assert.equal(layout.mediaBounds.width, layout.foregroundBounds.width);
});

test("retains a supplied focus point when smart-cropping a vertical video", () => {
  const layout = createComposition({ source: { width: 1080, height: 1920 }, focus: { x: 0.8, y: 0.2 } });
  assert.ok(layout.crop);
  if (!layout.crop) throw new Error("expected a portrait crop");
  assert.ok(layout.crop.retainedFocus.x > 0.45);
  assert.ok(layout.crop.retainedFocus.y > 0.1);
});

test("supports circle and non-standard source aspect ratios", () => {
  const layout = createComposition({ source: { width: 1733, height: 991 }, shape: "circle", density: 1 });
  assert.equal(layout.sourceAspect, "arbitrary");
  assert.equal(layout.clip.shape, "circle");
  assert.equal(layout.foregroundBounds.width, layout.foregroundBounds.height);
  assert.equal(layout.clip.cornerRadius, layout.foregroundBounds.width / 2);
});

test("recognizes the standard source aspect ratios", () => {
  const fixtures = [
    [1600, 900, "16:9"], [900, 1600, "9:16"], [1000, 1000, "1:1"],
    [1200, 900, "4:3"], [800, 1000, "4:5"],
  ] as const;
  for (const [width, height, expected] of fixtures) {
    const layout = createComposition({ source: { width, height } });
    assert.equal(layout.sourceAspect, expected);
    assert.ok(layout.foregroundBounds.width <= 304);
    assert.ok(layout.foregroundBounds.height <= 304);
  }
});

test("validates schema values", () => {
  assert.throws(() => createComposition({ source: { width: 0, height: 40 } }), /positive/);
  assert.throws(() => createComposition({ source: { width: 40, height: 40 }, density: 2 }), /density/);
});
