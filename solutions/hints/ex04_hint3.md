# ex04 — hint 3: Pseudocode / ready-made command

```python
from contextlib import contextmanager
import pyroscope

@contextmanager
def tag_wrapper(tags):
    with pyroscope.tag_wrapper(tags):
        yield
```
Full solution: `solutions/ex04_profiling.py`.
