# AI GIF Studio — Composition Engine

`createComposition()` produces a renderer-neutral plan for placing source video in a 320×320 canvas. It never stretches media: the returned `mediaScale` is uniform, and smart crops preserve a supplied normalized focus point.

The engine deliberately creates an internal foreground (70–95% scale) with breathing room. Consumers—especially a future Frame Engine—must follow `foregroundBounds` or `clip.bounds`; they must not draw around the canvas.

```ts
import { createComposition } from "./src/index.js";

const layout = createComposition({
  source: { width: 1920, height: 1080 },
  focus: { x: 0.65, y: 0.42 },
  shape: "rounded-rect",
  density: 0.6,
});
```

`crop.sourceBounds` is in original-video pixels. Render it into `mediaBounds`, then apply `clip`. The resulting foreground is appropriate for a frame to follow later.
