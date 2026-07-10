#!/usr/bin/env python3
"""Split a high-resolution photo into Claude-readable tiles, or crop a region.

Claude's vision pipeline downscales images to ~1.15 MP (~1568 px long edge),
so a full-frame Read of an 8+ MP photo loses most fine detail (stamped part
numbers, label text, hose-clamp counts). This tool emits pieces small enough
that no downscaling occurs.

Usage:
    # Full overlapping tile grid (survey mode — "describe everything")
    python3 split-photo.py photo.jpg

    # Zoom one region (targeted mode — cheapest, prefer this when you know
    # where to look). Fractions of width/height: left,top,right,bottom
    python3 split-photo.py photo.jpg --crop 0.4,0.2,0.8,0.6

    # Options
    python3 split-photo.py photo.jpg --out DIR --target 1200 --overlap 0.15

Output:
    Writes JPEG tiles to --out (default: a fresh mktemp dir under $TMPDIR)
    and prints one line per tile with its pixel span in the source image,
    so specific tiles can be Read selectively. Delete the output dir when
    done — tiles are throwaway working files, never committed.
"""
from __future__ import annotations

import argparse
import math
import pathlib
import sys
import tempfile

from PIL import Image

# Keep tile long edge under ~1568 px so the API doesn't downscale.
# base span TARGET + 2 * (TARGET * OVERLAP / 2) stays within that.
DEFAULT_TARGET = 1200
DEFAULT_OVERLAP = 0.15


def spans(total: int, target: int, overlap: float) -> list[tuple[int, int]]:
    """Split `total` pixels into overlapping spans of roughly `target` px."""
    n = max(1, math.ceil(total / target))
    if n == 1:
        return [(0, total)]
    base = total / n
    margin = int(base * overlap / 2)
    result = []
    for i in range(n):
        a = max(0, int(i * base) - margin)
        b = min(total, int((i + 1) * base) + margin)
        result.append((a, b))
    return result


def parse_crop(value: str) -> tuple[float, float, float, float]:
    parts = [float(p) for p in value.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("crop must be left,top,right,bottom fractions")
    l, t, r, b = parts
    if not (0 <= l < r <= 1 and 0 <= t < b <= 1):
        raise argparse.ArgumentTypeError("crop fractions must satisfy 0 <= left < right <= 1 (same for top/bottom)")
    return l, t, r, b


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("photo", type=pathlib.Path)
    ap.add_argument("--crop", type=parse_crop, default=None,
                    help="left,top,right,bottom as 0-1 fractions; emit one crop instead of a grid")
    ap.add_argument("--out", type=pathlib.Path, default=None,
                    help="output dir (default: fresh temp dir)")
    ap.add_argument("--target", type=int, default=DEFAULT_TARGET,
                    help=f"approx tile span in px before overlap (default {DEFAULT_TARGET})")
    ap.add_argument("--overlap", type=float, default=DEFAULT_OVERLAP,
                    help=f"fraction of tile span shared with neighbors (default {DEFAULT_OVERLAP})")
    args = ap.parse_args()

    if not args.photo.is_file():
        print(f"error: no such file: {args.photo}", file=sys.stderr)
        return 1

    out = args.out or pathlib.Path(tempfile.mkdtemp(prefix="photo-tiles-"))
    out.mkdir(parents=True, exist_ok=True)
    stem = args.photo.stem

    with Image.open(args.photo) as im:
        im = im.convert("RGB")
        w, h = im.size
        print(f"source: {args.photo}  ({w}x{h})")
        print(f"output: {out}")

        if args.crop:
            l, t, r, b = args.crop
            box = (int(l * w), int(t * h), int(r * w), int(b * h))
            crop = im.crop(box)
            # If the crop itself is still huge, shrink to the no-downscale limit.
            crop.thumbnail((1568, 1568))
            path = out / f"{stem}-crop.jpg"
            crop.save(path, quality=90)
            print(f"crop: {path}  px [{box[0]},{box[1]} - {box[2]},{box[3]}]  ({crop.size[0]}x{crop.size[1]})")
            return 0

        xs = spans(w, args.target, args.overlap)
        ys = spans(h, args.target, args.overlap)
        print(f"grid: {len(ys)} rows x {len(xs)} cols = {len(xs) * len(ys)} tiles "
              f"(row 1 = top, col 1 = left)")
        for ri, (y0, y1) in enumerate(ys, 1):
            for ci, (x0, x1) in enumerate(xs, 1):
                tile = im.crop((x0, y0, x1, y1))
                path = out / f"{stem}-r{ri}c{ci}.jpg"
                tile.save(path, quality=90)
                print(f"tile r{ri}c{ci}: {path}  px [{x0},{y0} - {x1},{y1}]  ({x1 - x0}x{y1 - y0})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
