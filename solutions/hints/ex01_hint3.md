# ex01 — hint 3: Pseudocode / ready-made command

```python
import pyroscope

def init_profiling(app_name, server_address, tags=None, wall=False):  # wall: ignored for now
    resolved_tags = tags or {}
    pyroscope.configure(
        application_name=app_name,
        server_address=server_address,
        sample_rate=100,
        oncpu=True,
        gil_only=True,
        tags=resolved_tags,
    )
    _STATE.update(configured=True, application_name=app_name,
                  server_address=server_address, tags=resolved_tags)
```
Full solution: `solutions/ex01_profiling.py`.
