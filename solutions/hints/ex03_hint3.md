# ex03 — hint 3: Pseudokod / gotowa komenda

```bash
python solutions/profile_sepia.py
snakeviz profiles/ex03_sepia.prof
```
Szukaj w wyniku stdout kolumn `tottime` i `cumtime` dla `_sepia_naive`
(u mnie `tottime` ok. 1,2 s z 1,5 s łącznie; `min` wołane 9 000 000 razy).
Lista na stdout jest posortowana wg `cumtime`; pełny ranking wg czasu własnego
daje podgląd bez przeglądarki: `python -m pstats profiles/ex03_sepia.prof`,
potem w jego znaku zachęty wpisz `sort tottime`, `stats 5` i `quit`.
