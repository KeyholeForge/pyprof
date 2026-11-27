# ex05 — hint 3: Pseudocode / ready-made command

```python
SEPIA_MATRIX = (
    0.393, 0.769, 0.189, 0,
    0.349, 0.686, 0.168, 0,
    0.272, 0.534, 0.131, 0,
)
# in apply_filter, the "sepia" branch:
result = img.convert("RGB", matrix=SEPIA_MATRIX)
```
Full solution: `solutions/filters_snippets.py`.
