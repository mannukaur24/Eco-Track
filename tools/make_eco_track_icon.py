"""Generate a simple original green environmental EcoTrack Windows icon (.ico).

Draws a dark-green rounded-square background with a lighter-green leaf motif
and stem. Outputs a single 256x256 32-bit (alpha) icon image, which Windows
scales down for all shell sizes.

The ICO container is written by hand (no Pillow dependency):

ICONDIR (6 bytes) + ICONDIRENTRY (16 bytes) + BMP image
(BITMAPINFOHEADER 40 bytes + 32bpp top-down BGRA pixels).
"""

import struct
from pathlib import Path

ICON_SIZE = 256
STRIDE = ICON_SIZE * 4  # 32bpp rows are 4-byte aligned

# EcoTrack brand greens.
GREEN_DARK = (27, 94, 32, 255)    # #1B5E20 background
GREEN_LEAF = (76, 175, 80, 230)   # #4CAF50 leaf
GREEN_STEM = (51, 105, 30, 255)   # #33691E stem
WHITE_SOFT = (255, 255, 255, 90)  # subtle highlight


def premultiply(color):
    r, g, b, a = color
    return (r * a // 255, g * a // 255, b * a // 255, a)


def alpha_blend(dst, src):
    """Composite premultiplied src over premultiplied dst; both RGBA 0-255."""
    sa = src[3] / 255.0
    da = dst[3] / 255.0
    out_a = sa + da * (1.0 - sa)
    if out_a == 0:
        return (0, 0, 0, 0)
    out_r = (src[0] + dst[0] * (1.0 - sa)) / out_a
    out_g = (src[1] + dst[1] * (1.0 - sa)) / out_a
    out_b = (src[2] + dst[2] * (1.0 - sa)) / out_a
    return (
        int(round(min(255, out_r * 255))),
        int(round(min(255, out_g * 255))),
        int(round(min(255, out_b * 255))),
        int(round(min(255, out_a * 255))),
    )


def fill_rounded_rect(buf, w, h, x0, y0, x1, y1, radius, color):
    c = premultiply(color)
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            # Corner cut-out test
            cut = False
            for cx, cy in ((x0 + radius, y0 + radius),
                           (x1 - radius, y0 + radius),
                           (x0 + radius, y1 - radius),
                           (x1 - radius, y1 - radius)):
                dx = x - cx
                dy = y - cy
                if dx < 0 and dy < 0 and dx * dx + dy * dy > radius * radius:
                    cut = True
            if not (x0 <= x <= x1 and y0 <= y <= y1):
                continue
            if cut:
                continue
            buf[(y * w + x) * 4:(y * w + x) * 4 + 4] = bytes(c)


def fill_ellipse(buf, w, h, cx, cy, rx, ry, color):
    c = premultiply(color)
    rx2 = rx * rx
    ry2 = ry * ry
    for y in range(max(0, cy - ry), min(h, cy + ry + 1)):
        dy = y - cy
        row = y * w * 4
        for x in range(max(0, cx - rx), min(w, cx + rx + 1)):
            dx = x - cx
            if dx * dx * ry2 + dy * dy * rx2 <= rx2 * ry2:
                buf[row + x * 4:row + x * 4 + 4] = bytes(c)


def composite_buffer(base, overlay):
    out = bytearray(base)
    stride4 = 4
    for i in range(0, len(out), stride4):
        dst = tuple(out[i:i + stride4])
        src = tuple(overlay[i:i + stride4])
        if src == (0, 0, 0, 0):
            continue
        blended = alpha_blend(dst, src)
        out[i:i + stride4] = bytes(blended)
    return bytes(out)


def build_icon_buffer():
    w = h = ICON_SIZE
    buf = bytearray(w * h * 4)  # transparent

    # Background: dark green rounded square.
    overlay = bytearray(w * h * 4)
    fill_rounded_rect(overlay, w, h, 0, 0, w - 1, h - 1, 44, GREEN_DARK)
    buf = composite_buffer(bytes(buf), overlay)

    # Leaf: two overlapping ellipses.
    overlay = bytearray(w * h * 4)
    cx = w // 2
    cy = int(h * 0.52)
    fill_ellipse(overlay, w, h, cx - 34, cy - 10, 66, 78, GREEN_LEAF)
    fill_ellipse(overlay, w, h, cx + 34, cy - 10, 66, 78, GREEN_LEAF)
    # Highlight over the leaf.
    overlay2 = bytearray(w * h * 4)
    fill_ellipse(overlay2, w, h, cx - 14, cy - 40, 30, 34, WHITE_SOFT)
    overlay = composite_buffer(bytes(overlay), bytes(overlay2))
    buf = composite_buffer(bytes(buf), bytes(overlay))

    # Stem.
    overlay = bytearray(w * h * 4)
    fill_rounded_rect(overlay, w, h, cx - 8, int(h * 0.20), cx + 8, cy - 42, 6, GREEN_STEM)
    buf = composite_buffer(bytes(buf), bytes(overlay))

    return bytes(buf)


def bmp_32bit_topdown(pixels, width, height):
    header = struct.pack(
        "<iiiHHiIiiII",
        40,            # biSize
        width,         # biWidth
        -height,       # biHeight (top-down, negative)
        1,             # biPlanes
        32,            # biBitCount
        0,             # biCompression = BI_RGB
        0,             # biSizeImage
        0,             # biXPelsPerMeter
        0,             # biYPelsPerMeter
        0,             # biClrUsed
        0,             # biClrImportant
    )
    return header + pixels


def build_ico(pixels, width, height):
    image = bmp_32bit_topdown(pixels, width, height)
    icon_dir = struct.pack("<HHH", 0, 1, 1)  # reserved, type=1, count=1
    # bWidth/bHeight = 0 means 256.
    entry = struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(image), 6 + 16)
    return icon_dir + entry + image


def main():
    pixels = build_icon_buffer()
    ico = build_ico(pixels, ICON_SIZE, ICON_SIZE)

    out_path = Path(__file__).resolve().parent.parent / "assets" / "EcoTrack.ico"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(ico)
    print("Wrote %s (%d bytes)" % (out_path, len(ico)))


if __name__ == "__main__":
    main()
