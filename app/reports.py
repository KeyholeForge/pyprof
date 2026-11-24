"""Batch reports (CSV) with the metadata of many images.

This module WORKS from the start, and the version in `app/` is CORRECT: it builds a list
of lines and joins it with ONE `"\\n".join()` at the end — there is no performance flaw.

NOTE (exercise 09, ★ Bonus B, F7 — introduced by an instruction, not built in from the start):
in ★ Bonus B of exercise 09 the learner deliberately BREAKS the function `generate_batch_report`
below: replaces building a list + `join()` with string concatenation in a loop
(`report = ""; report += line + "\\n"`), measures it and sees in the profile that this is NOT
the bottleneck: the report time is `Image.open()` and I/O (1000 IDs: 25.6 ms with `+=`
and 25.5 ms with `join()`), and CPython extends the string in place. Conclusion: a micro-optimization
without a measurement makes no sense. The broken version should NOT stay in the repo.
See solutions/reports_snippets.py — both versions and the measurement results.
"""

from __future__ import annotations

from PIL import Image

from . import images as images_module


def generate_batch_report(image_ids: list[str]) -> str:
    """Generates a CSV report (a header + one line per image) for a list of IDs.

    Columns: id, format, width, height, size_bytes.
    Images that cannot be opened (deleted/nonexistent IDs) go into the report
    with error columns instead of aborting the whole report.
    """
    lines = ["id,format,width,height,size_bytes"]  # the CORRECT version: list + join
    for image_id in image_ids:
        try:
            path = images_module._image_path(image_id)
            with Image.open(path) as img:
                fmt = img.format or "?"
                width, height = img.size
            size_bytes = path.stat().st_size
            lines.append(f"{image_id},{fmt},{width},{height},{size_bytes}")
        except images_module.ImageNotFoundError:
            lines.append(f"{image_id},ERROR,,,not_found")
    return "\n".join(lines)  # one join at the end, not in the loop
