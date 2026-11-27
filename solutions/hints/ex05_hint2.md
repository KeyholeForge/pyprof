# ex05 — hint 2: Which API/tool

`Image.convert("RGB", matrix=...)` takes 12 coefficients (4 per output
channel R/G/B: the R, G, B multipliers + an offset). The sepia coefficients are
identical to the ones already used in `_sepia_naive` (0.393/0.769/0.189 etc.).
