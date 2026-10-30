"""Generate the app icons (a macro-split donut on deep teal) with no image dependencies.

The donut is cut into protein, carbs and fat in the app's macro colors. PWA icons are full-bleed with a soft glow;
the favicons drop the glow, thicken the ring and sit on a rounded tile so they stay legible at 16 px.

Run: uv run python scripts/make_icons.py
"""

import math
import struct
import zlib
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "app" / "static" / "icons"
BG = (12, 59, 56)  # #0c3b38
# (color, start, length) as percentages of the ring, clockwise from 12 o'clock; the gaps between them are empty.
SEGMENTS = [((96, 165, 250), 0, 38), ((74, 222, 128), 41, 34), ((232, 121, 249), 78, 19)]
# Geometry on a 512 canvas: (ring radius, ring width).
LARGE = (118, 62)
SMALL = (128, 78)
TILE_RADIUS = 112  # favicon tile corner radius, on the same 512 canvas
GLOW_SIGMA = 10


def _hex(color: tuple[int, int, int]) -> str:
    return "#" + "".join(f"{c:02x}" for c in color)


def _png(size: int, pixels: list[list[tuple[int, ...]]], alpha: bool) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + bytes(channel for pixel in row for channel in pixel) for row in pixels)
    header = struct.pack(">IIBBBBB", size, size, 8, 6 if alpha else 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def _segment_at(x: float, y: float, c: float, r: float, w: float):
    """Segment color at a point, or None if the point is off the ring or in a gap."""
    dx, dy = x - c, y - c
    if abs(math.hypot(dx, dy) - r) > w / 2:
        return None
    pct = (math.degrees(math.atan2(dx, -dy)) % 360) / 3.6
    for color, start, length in SEGMENTS:
        if start <= pct < start + length:
            return color
    return None


def _ring(size: int, geometry: tuple[int, int]) -> list[list[tuple[float, float, float, float]]]:
    """Antialiased ring as premultiplied RGBA floats, supersampling only pixels near an edge."""
    scale = size / 512
    c, r, w = size / 2, geometry[0] * scale, geometry[1] * scale
    edges = [s / 100 * 2 * math.pi for _, start, length in SEGMENTS for s in (start, start + length)]
    n = 4
    layer = []
    for py in range(size):
        row = []
        for px in range(size):
            x, y = px + 0.5, py + 0.5
            d = math.hypot(x - c, y - c)
            angle = math.atan2(x - c, -(y - c)) % (2 * math.pi)
            near = min(abs(d - (r - w / 2)), abs(d - (r + w / 2)), min(d * abs(angle - e) for e in edges)) < 1.5
            samples = [(px + (i + 0.5) / n, py + (j + 0.5) / n) for i in range(n) for j in range(n)] if near else [(x, y)]
            acc = [0.0, 0.0, 0.0, 0.0]
            for sx, sy in samples:
                color = _segment_at(sx, sy, c, r, w)
                if color:
                    acc[0] += color[0]
                    acc[1] += color[1]
                    acc[2] += color[2]
                    acc[3] += 1
            k = len(samples)
            row.append((acc[0] / k, acc[1] / k, acc[2] / k, acc[3] / k))
        layer.append(row)
    return layer


def _blur(layer, sigma: float):
    """Approximate Gaussian blur: three separable box blurs on a quarter-size copy, scaled back up."""
    size = len(layer)
    f = 4
    small_size = size // f
    small = [[tuple(sum(layer[y * f + j][x * f + i][ch] for i in range(f) for j in range(f)) / (f * f) for ch in range(4))
              for x in range(small_size)] for y in range(small_size)]
    radius = max(1, round(math.sqrt(12 * (sigma / f) ** 2 / 3 + 1) / 2))

    def box(line):
        out, acc, width = [], [0.0] * 4, 2 * radius + 1
        padded = [(0.0,) * 4] * radius + line + [(0.0,) * 4] * radius
        for i in range(width):
            acc = [a + b for a, b in zip(acc, padded[i])]
        for i in range(len(line)):
            out.append(tuple(a / width for a in acc))
            if i + width < len(padded):
                acc = [a + b - d for a, b, d in zip(acc, padded[i + width], padded[i])]
        return out

    for _ in range(3):
        small = [box(row) for row in small]
        small = [list(col) for col in zip(*[box(list(col)) for col in zip(*small)])]
    # Bilinear upsample back to full size.
    out = []
    for y in range(size):
        fy = min(max((y + 0.5) / f - 0.5, 0), small_size - 1)
        y0, ty = int(fy), fy - int(fy)
        y1 = min(y0 + 1, small_size - 1)
        row = []
        for x in range(size):
            fx = min(max((x + 0.5) / f - 0.5, 0), small_size - 1)
            x0, tx = int(fx), fx - int(fx)
            x1 = min(x0 + 1, small_size - 1)
            row.append(tuple(
                (small[y0][x0][ch] * (1 - tx) + small[y0][x1][ch] * tx) * (1 - ty)
                + (small[y1][x0][ch] * (1 - tx) + small[y1][x1][ch] * tx) * ty
                for ch in range(4)
            ))
        out.append(row)
    return out


def _over(dst: tuple[float, float, float], src: tuple[float, float, float, float]) -> tuple[float, float, float]:
    return tuple(src[i] + dst[i] * (1 - src[3]) for i in range(3))


def _tile_coverage(px: int, py: int, size: int) -> float:
    """How much of a pixel lies inside the rounded favicon tile (4x4 supersampled near the corners)."""
    rad = TILE_RADIUS * size / 512
    n = 4
    inside = 0
    for i in range(n):
        for j in range(n):
            x, y = px + (i + 0.5) / n, py + (j + 0.5) / n
            cx, cy = min(max(x, rad), size - rad), min(max(y, rad), size - rad)
            inside += math.hypot(x - cx, y - cy) <= rad
    return inside / (n * n)


def draw_app_icon(size: int) -> bytes:
    """Full-bleed PWA / Apple touch icon: the large ring with its glow on solid teal."""
    ring = _ring(size, LARGE)
    glow = _blur(ring, GLOW_SIGMA * size / 512)
    pixels = []
    for y in range(size):
        row = []
        for x in range(size):
            color = _over(_over(BG, glow[y][x]), ring[y][x])
            row.append(tuple(round(min(255, c)) for c in color))
        pixels.append(row)
    return _png(size, pixels, alpha=False)


def draw_favicon(size: int) -> bytes:
    """Favicon PNG: the thicker ring, no glow, on a rounded tile with transparent corners."""
    ring = _ring(size, SMALL)
    pixels = []
    for y in range(size):
        row = []
        for x in range(size):
            color = _over(BG, ring[y][x])
            row.append((*(round(c) for c in color), round(255 * _tile_coverage(x, y, size))))
        pixels.append(row)
    return _png(size, pixels, alpha=True)


def favicon_svg() -> str:
    r, w = SMALL
    circles = "".join(
        f'<circle cx="256" cy="256" r="{r}" fill="none" stroke="{_hex(color)}" stroke-width="{w}" pathLength="100" '
        f'stroke-dasharray="{length} {100 - length}" stroke-dashoffset="{-start}" transform="rotate(-90 256 256)"/>'
        for color, start, length in SEGMENTS
    )
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">'
            f'<rect width="512" height="512" rx="{TILE_RADIUS}" fill="{_hex(BG)}"/>{circles}</svg>\n')


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, size in [("icon-192.png", 192), ("icon-512.png", 512), ("apple-touch-icon.png", 180)]:
        (OUT / name).write_bytes(draw_app_icon(size))
        print(f"wrote {OUT / name}")
    (OUT / "favicon-32.png").write_bytes(draw_favicon(32))
    print(f"wrote {OUT / 'favicon-32.png'}")
    (OUT / "favicon.svg").write_text(favicon_svg())
    print(f"wrote {OUT / 'favicon.svg'}")
