# ex01 — hint 1: Direction

You need to connect the application to Pyroscope AT STARTUP, before the first
request arrives — look at `lifespan` in `app/main.py`, which already calls
`profiling.init_profiling(...)`. Your task is to fill in the `init_profiling`
function itself in `app/profiling.py`.

If you see nothing in Pyroscope after the restart: check `curl -s 127.0.0.1:8040/health` (`configured: true`?), generate traffic AFTER the start and wait 15–20 s.
