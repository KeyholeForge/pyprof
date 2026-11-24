# ex01 — hint 3: Pseudokod / gotowa komenda

```python
import pyroscope

def init_profiling(app_name, server_address, tags=None, wall=False):  # wall: na razie ignorowany
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
Pełne rozwiązanie: `solutions/ex01_profiling.py`.
