#!/usr/bin/env python3
"""生成 PWA / iOS 主屏幕图标（纯标准库，无 Pillow 依赖）。

图形：深蓝渐变底 + 白色文献卡片 + 红色番茄标记。
内容集中在中央 54% 区域，兼容 Android maskable 图标的安全区。
运行：python scripts/generate_icons.py
"""
from __future__ import annotations

import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGETS = [
    (ROOT / "public" / "apple-touch-icon.png", 180),
    (ROOT / "public" / "icon-192.png", 192),
    (ROOT / "public" / "icon-512.png", 512),
    (ROOT / "app" / "icon.png", 64),
]


def inside_rounded_rect(x, y, x0, y0, x1, y1, r):
    if x < x0 or x > x1 or y < y0 or y > y1:
        return False
    qx = max(x0 + r, min(x, x1 - r))
    qy = max(y0 + r, min(y, y1 - r))
    return (x - qx) ** 2 + (y - qy) ** 2 <= r * r


def sample(u: float, v: float) -> tuple[int, int, int]:
    t = (u + v) / 2
    background = (int(15 + 22 * t), int(23 + 40 * t), int(42 + 55 * t))

    # 番茄标记（红色圆点），画在卡片上层作为徽标
    if (u - 0.685) ** 2 + (v - 0.275) ** 2 <= 0.072 ** 2:
        return (239, 68, 68)

    if inside_rounded_rect(u, v, 0.27, 0.19, 0.73, 0.81, 0.055):
        for line_y, width in ((0.44, 0.26), (0.555, 0.30), (0.67, 0.20)):
            if line_y - 0.017 <= v <= line_y + 0.017 and 0.35 <= u <= 0.35 + width:
                return (51, 65, 85)  # 文字行
        return (255, 255, 255)

    return background


def write_png(path: Path, size: int) -> None:
    raw = bytearray()
    for y in range(size):
        raw.append(0)  # PNG filter: None
        for x in range(size):
            acc = [0, 0, 0]
            for dy in (0.25, 0.75):
                for dx in (0.25, 0.75):
                    r, g, b = sample((x + dx) / size, (y + dy) / size)
                    acc[0] += r
                    acc[1] += g
                    acc[2] += b
            raw.extend(v // 4 for v in acc)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)  # 8-bit RGB，不透明
    blob = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(blob)
    print(f"wrote {path.relative_to(ROOT)} ({size}x{size}, {len(blob)} bytes)")


if __name__ == "__main__":
    for target, dimension in TARGETS:
        write_png(target, dimension)
