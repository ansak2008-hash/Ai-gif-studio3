# Crop Only Engine

Standalone Python API for the strictly non-design conversion path:

```python
from crop_only_engine import crop_video_to_gif

result = crop_video_to_gif("input.mp4", "output.gif")
```

It performs a genuine largest-possible centred 1:1 crop, Lanczos scales to
320×320, and encodes directly to GIF with a per-output palette and dithering.
It neither stretches video nor applies a frame, background, design effect,
smart-design logic, or intentional colour transformation. Videos longer than
six seconds are represented by their temporal-centre six-second segment.

The runtime requires `ffmpeg` and `ffprobe` on `PATH`. The configurable FPS
ladder is attempted from highest to lowest until the GIF is at most 2,400,000
bytes; a conversion that cannot meet that hard limit raises `CropOnlyError`.
