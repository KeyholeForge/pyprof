# ex03 — hint 3: Pseudocode / ready-made command

```bash
python solutions/profile_sepia.py
snakeviz profiles/ex03_sepia.prof
```
Look in the stdout output for the `tottime` and `cumtime` columns for `_sepia_naive`
(in my run `tottime` is about 1.2 s out of 1.5 s total; `min` called 9,000,000 times).
The stdout list is sorted by `cumtime`; for the full ranking by own time use
the preview without a browser: `python -m pstats profiles/ex03_sepia.prof`, then
type `sort tottime`, `stats 5` and `quit` at its prompt.
