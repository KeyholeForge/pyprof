# ex01 — hint 2: Which API/tool

Use `pyroscope.configure(...)` from the `pyroscope-io` package (already in
`requirements.txt`; add `import pyroscope` at the top of `app/profiling.py`).
Parameters: `application_name`, `server_address`, `sample_rate=100`,
`oncpu=True`, `gil_only=True`, `tags`. After the call, update the `_STATE`
dictionary.

The signature also has a `wall` parameter — you do not use it in this exercise (you will handle it in exercise 11).
