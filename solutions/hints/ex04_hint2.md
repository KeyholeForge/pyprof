# ex04 — hint 2: Which API/tool

`pyroscope.tag_wrapper(tags: dict)` is a ready-made context manager from
pyroscope-io — your function just calls it with `with` and `yield`.

Note: tags are set per thread — this works for `def` endpoints (a synchronous handler runs on one pool worker thread while it executes); for `async def` the tags of concurrent requests get mixed (exercise 11).
