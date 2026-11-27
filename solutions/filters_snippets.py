"""solutions/filters_snippets.py — the fixed version of the "sepia" filter (exercise 05, F2).

This is NOT a file to swap in 1:1 — it shows only a snippet to move over by hand
to app/images.py: replace the call of `_sepia_naive` in `apply_filter` with the
version below, which computes sepia with a single Pillow operation instead of a
pure-Python loop. Keep the definition of `_sepia_naive` in app/images.py:
`solutions/profile_sepia.py` and exercise 06 import it.

The idea of the fix: sepia is a LINEAR transform of the RGB channels — it can be written
as a 3x3 matrix multiplication (+ an offset), and Pillow has a built-in operation for
it that runs the per-pixel loop in C: `Image.convert("RGB", matrix=...)`. Instead of
3,000,000 iterations of the Python interpreter (2000x1500 pixels), the whole operation
happens in native code. Both versions are still linear in the number of pixels.
"""

from __future__ import annotations

from PIL import Image

# The sepia matrix in the format expected by Image.convert("RGB", matrix=...):
# 12 coefficients (4 per output channel: the R, G, B multipliers + an offset), that is
# out_R = m[0]*R + m[1]*G + m[2]*B + m[3]
# out_G = m[4]*R + m[5]*G + m[6]*B + m[7]
# out_B = m[8]*R + m[9]*G + m[10]*B + m[11]
SEPIA_MATRIX = (
    0.393, 0.769, 0.189, 0,
    0.349, 0.686, 0.168, 0,
    0.272, 0.534, 0.131, 0,
)


def sepia_fast(img: Image.Image) -> Image.Image:
    """A replacement for `_sepia_naive` from app/images.py — no Python loop.

    Note: Image.convert with a matrix rounds each channel to the nearest
    integer and clips it to 0-255 itself, in the same operation; the naive
    loop truncates (`int`) and caps with `min(255, ...)`. A channel value may
    differ by 1 level — visually equivalent, not bit-for-bit identical.
    """
    rgb = img.convert("RGB")
    return rgb.convert("RGB", matrix=SEPIA_MATRIX)


# In app/images.py:
#
#   from PIL import Image
#
#   def apply_filter(image_id: str, name: str) -> bytes:
#       ...
#       elif name == "sepia":
#           result = img.convert("RGB", matrix=SEPIA_MATRIX)   # <-- instead of _sepia_naive(img)
#       ...
#
# Keep the definition of `_sepia_naive` (exercise 06 and solutions/profile_sepia.py
# import it, and it is useful for a before/after comparison); remove only its call.
