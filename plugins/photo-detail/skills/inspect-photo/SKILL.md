---
description: Read a high-resolution photo at full detail by tiling it or cropping one region — use when fine detail (label text, part numbers, small components) matters and a plain Read is too downscaled to resolve it.
---

# Inspect Photo (full-resolution tiling)

Claude's vision pipeline downscales images to ~1.15 MP, so a direct Read of a
high-res photo (phone/action-cam, 8–50 MP) loses most fine detail. This skill
recovers it by Reading pieces small enough to escape downscaling.

Photo to inspect: $ARGUMENTS

## Workflow

1. **Read the original photo first** for a low-res overview and to decide what
   you actually need from it. If the overview already answers the question,
   stop — do not tile.

2. **Prefer crop mode when you know where to look** (one Read instead of many):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/split-photo.py" <photo> --crop 0.4,0.2,0.8,0.6
   ```

   Fractions are left,top,right,bottom of the frame. Iterate: re-crop tighter
   if the first crop is still too coarse.

3. **Tile mode for full-frame surveys** ("catalog everything visible"):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/split-photo.py" <photo>
   ```

   It prints the output dir and a grid map (`r1c1` = top-left) with pixel
   spans. Read tiles selectively using the map when possible; Read all of them
   only for a true full survey. Tiles overlap ~15% so nothing is lost at seams
   — expect objects near tile edges to appear twice; dedupe when synthesizing.

4. **Synthesize findings into the docs, referencing the ORIGINAL photo path**,
   never a tile path.

5. **Delete the output dir** (`rm -rf <printed temp dir>`). Tiles are
   throwaway working files — never commit them into the project.

## Cost & limits

- Each tile/crop Read costs roughly what one image Read always costs
  (~1.5k tokens). Tile counts by source resolution:
  ~8.8 MP → ~8 tiles; ~12.5 MP → ~12 tiles; ~50 MP → ~40+ tiles.
  At 50 MP, full tiling is expensive — crop mode or a two-pass approach
  (tile at `--target 3000` for a mid-res pass, then full-res crop only the
  interesting regions) is strongly preferred.
- Tiling recovers **resolution, not focus** — a motion-blurred or misfocused
  source will not improve. Say so rather than guessing at illegible detail.
- Stylized text (script logos, decorative badges) can read "cleanly" and still
  be wrong — treat confident reads of stylized lettering as candidates and
  corroborate against a second source (another photo, known model names)
  before writing them into docs.
