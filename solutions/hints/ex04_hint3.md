# ex04 — hint 3: Pseudokod / gotowa komenda

```python
from contextlib import contextmanager
import pyroscope

@contextmanager
def tag_wrapper(tags):
    with pyroscope.tag_wrapper(tags):
        yield
```
Pełne rozwiązanie: `solutions/ex04_profiling.py`.
