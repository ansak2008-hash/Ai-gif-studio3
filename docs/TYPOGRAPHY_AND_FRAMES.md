# Typography, Calligraphy, Frames & Backgrounds

The deterministic Design GIF pipeline now supports a bounded visual system for names, Arabic/Latin text, materials, frames and backgrounds.

## Typography
- Arabic and Latin script detection.
- Safe logical font resolution; no arbitrary font path is accepted from the API.
- FFmpeg text shaping is requested for Arabic/RTL when the FFmpeg build provides the required shaping libraries.
- Styles: flat, bold, calligraphy, 3d, extruded, gold, silver, chrome, neon.
- Materials: flat, gold, silver, chrome, neon.
- 3D/extruded appearance uses deterministic depth layers.
- Metallic appearance uses layered highlight/shadow passes rather than claiming physically based rendering.

## Frames
- simple / rounded / classic
- double / royal
- gold
- silver / chrome
- neon

## Backgrounds
- solid
- duotone
- stripes
- luxury
- sunset

## Motion
The existing bounded float/pan motion remains available and is independent from typography material.

## Licensing
Noto Arabic is an upstream open font project distributed under SIL Open Font License 1.1. If fonts are bundled into a release, the applicable license and copyright notices must ship with them. Proprietary/decorative fonts must not be copied into the repository without a compatible license.

## Important boundary
"3D" here means deterministic visual depth/extrusion in the 2D GIF render. "4D" is treated as time-varying animation of the 3D-style visual, not a physical fourth spatial dimension.
