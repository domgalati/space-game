"""Extract the BARGE from the ship mockup and build a 6-frame game sheet."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance

SRC = Path(__file__).with_name("ship-mockup-designs.jpg")
OUT = Path(__file__).with_name("barge6frame.png")
SOURCE_OUT = Path(__file__).with_name("_barge_source.png")
FRAME = 96
FRAMES = 6


def load_barge() -> Image.Image:
    im = Image.open(SRC).convert("RGBA")
    crop = im.crop((735, 100, 955, 405))
    arr = np.array(crop)
    rgb = arr[:, :, :3].astype(np.int16)
    arr[rgb.max(axis=2) < 24, 3] = 0

    alpha = arr[:, :, 3] > 0
    ys, xs = np.where(alpha)
    cy, cx = int(ys.mean()), int(xs.mean())
    h, w = alpha.shape
    visited = np.zeros_like(alpha, dtype=bool)
    stack = [(cy, cx)] if alpha[cy, cx] else [(int(ys[0]), int(xs[0]))]
    while stack:
        y, x = stack.pop()
        if y < 0 or y >= h or x < 0 or x >= w or visited[y, x] or not alpha[y, x]:
            continue
        visited[y, x] = True
        stack.extend(((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)))
    arr[~visited, 3] = 0

    ys, xs = np.where(arr[:, :, 3] > 0)
    pad = 2
    y0 = max(0, ys.min() - pad)
    y1 = min(arr.shape[0], ys.max() + pad + 1)
    x0 = max(0, xs.min() - pad)
    x1 = min(arr.shape[1], xs.max() + pad + 1)
    return Image.fromarray(arr[y0:y1, x0:x1])


def fit_frame(ship: Image.Image, size: int) -> Image.Image:
    # Keep a few pixels below for plume stretch; keep sides tight.
    max_w = size - 6
    max_h = size - 8
    scale = min(max_w / ship.width, max_h / ship.height)
    new_w = max(1, int(round(ship.width * scale)))
    new_h = max(1, int(round(ship.height * scale)))
    scaled = ship.resize((new_w, new_h), Image.Resampling.LANCZOS)
    scaled = ImageEnhance.Contrast(scaled).enhance(1.05)
    scaled = ImageEnhance.Sharpness(scaled).enhance(1.15)

    frame = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    x = (size - new_w) // 2
    y = max(1, (size - new_h) // 2 - 2)
    frame.paste(scaled, (x, y), scaled)
    return frame


def rear_flame_mask(arr: np.ndarray) -> np.ndarray:
    r, g, b, a = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3]
    warm = (a > 0) & (r > 150) & (g > 50) & (b < 130) & (r + 20 > g)
    # Rear thrusters live in the lower third.
    warm[: arr.shape[0] * 2 // 3, :] = False
    return warm


def animate(base: Image.Image, frame_idx: int) -> Image.Image:
    """Subtle plume flicker that keeps the original thruster look."""
    arr = np.array(base).copy()
    mask = rear_flame_mask(arr)
    if not mask.any():
        return base

    # Brightness / saturation pulses per frame.
    pulses = [0.78, 0.92, 1.12, 1.00, 0.88, 0.72]
    pulse = pulses[frame_idx]

    flame = arr[mask].astype(np.float32)
    flame[:, 0] = np.clip(flame[:, 0] * pulse, 0, 255)
    flame[:, 1] = np.clip(flame[:, 1] * (0.85 + 0.15 * pulse), 0, 255)
    flame[:, 2] = np.clip(flame[:, 2] * 0.9, 0, 255)
    arr[mask] = flame.astype(np.uint8)

    # Stretch or shrink plume tips a couple of pixels for motion.
    ys, xs = np.where(mask)
    y_tip = ys.max()
    tip = mask.copy()
    tip[: y_tip - 2, :] = False
    extend = [0, 1, 2, 1, 1, 0][frame_idx]
    if extend:
        for y, x in zip(*np.where(tip)):
            src = arr[y, x]
            for dy in range(1, extend + 1):
                yy = y + dy
                if yy >= arr.shape[0]:
                    break
                if arr[yy, x, 3] == 0:
                    fade = max(40, 255 - dy * 70)
                    arr[yy, x] = (src[0], max(0, src[1] - 20 * dy), src[2], fade)
    else:
        # Retract tip slightly on dim frames.
        for y, x in zip(*np.where(tip)):
            if frame_idx in (0, 5) and y >= y_tip - 1:
                arr[y, x, 3] = max(0, arr[y, x, 3] // 2)

    # Alternate left/right thruster emphasis for flicker.
    mid_x = arr.shape[1] // 2
    if frame_idx == 4:
        left = mask & (np.arange(arr.shape[1])[None, :] < mid_x)
        right = mask & ~left
        arr[right, 0] = np.clip(arr[right, 0].astype(np.int16) + 25, 0, 255).astype(np.uint8)
        arr[left, 0] = np.clip(arr[left, 0].astype(np.int16) - 15, 0, 255).astype(np.uint8)

    return Image.fromarray(arr)


def main():
    barge = load_barge()
    barge.save(SOURCE_OUT)
    base = fit_frame(barge, FRAME)
    sheet = Image.new("RGBA", (FRAME * FRAMES, FRAME), (0, 0, 0, 0))
    for i in range(FRAMES):
        frame = animate(base, i)
        sheet.paste(frame, (i * FRAME, 0), frame)
    sheet.save(OUT)
    print("wrote", OUT, sheet.size, "source", barge.size)


if __name__ == "__main__":
    main()
