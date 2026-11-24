# ex04 — hint 2: Które API/narzędzie

`pyroscope.tag_wrapper(tags: dict)` to gotowy context manager z
pyroscope-io — Twoja funkcja tylko go woła przez `with` i `yield`.

Uwaga: tagi są ustawiane na wątek — działa dla endpointów `def` (synchroniczny handler działa na jednym wątku roboczym z puli przez czas wykonania); dla `async def` tagi współbieżnych żądań się mieszają (ćwiczenie 11).
