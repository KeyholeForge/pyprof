# ex01 — hint 2: Które API/narzędzie

Użyj `pyroscope.configure(...)` z pakietu `pyroscope-io` (już w
`requirements.txt`; dodaj `import pyroscope` na górze `app/profiling.py`).
Parametry: `application_name`, `server_address`, `sample_rate=100`,
`oncpu=True`, `gil_only=True`, `tags`. Po wywołaniu zaktualizuj słownik
`_STATE`.

Sygnatura ma też parametr `wall` — w tym ćwiczeniu go nie używasz (obsłużysz go w ćwiczeniu 11).
