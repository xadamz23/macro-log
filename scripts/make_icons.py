"""Generate PWA icons (three macro bars on green) with no image dependencies.

Run: uv run python scripts/make_icons.py
"""

import struct
import zlib
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "app" / "static" / "icons"
BG = (47, 111, 78)
TRACK = (36, 88, 61)
BARS = [((217, 119, 6), 0.80), ((96, 165, 250), 0.60), ((52, 211, 153), 0.45)]


def _png(size: int, rows: list[bytes]) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + row for row in rows)
    header = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def draw(size: int) -> bytes:
    pixels = [[BG] * size for _ in range(size)]
    margin, bar_h, gap = size * 0.2, size * 0.11, size * 0.07
    top = (size - (3 * bar_h + 2 * gap)) / 2
    x0, x1 = int(margin), int(size - margin)
    for i, (color, fraction) in enumerate(BARS):
        y0 = int(top + i * (bar_h + gap))
        filled_to = int(x0 + (x1 - x0) * fraction)
        for y in range(y0, int(y0 + bar_h)):
            for x in range(x0, x1):
                pixels[y][x] = color if x < filled_to else TRACK
    rows = [bytes(channel for pixel in row for channel in pixel) for row in pixels]
    return _png(size, rows)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, size in [("icon-192.png", 192), ("icon-512.png", 512), ("apple-touch-icon.png", 180)]:
        (OUT / name).write_bytes(draw(size))
        print(f"wrote {OUT / name}")
