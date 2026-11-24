# ex01 — hint 1: Kierunek

Musisz podłączyć aplikację do Pyroscope PRZY STARCIE, zanim przyjdzie
pierwszy request — spójrz na `lifespan` w `app/main.py`, które już wywołuje
`profiling.init_profiling(...)`. Twoje zadanie to wypełnić samą funkcję
`init_profiling` w `app/profiling.py`.

Jeśli po restarcie nie widzisz niczego w Pyroscope: sprawdź `curl -s 127.0.0.1:8040/health` (`configured: true`?), wygeneruj ruch PO starcie i odczekaj 15–20 s.
