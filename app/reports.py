"""Raporty wsadowe (CSV) z metadanymi wielu obrazów.

Ten moduł DZIAŁA od startu i w wersji w `app/` jest POPRAWNY: buduje listę
linii i łączy ją JEDNYM `"\\n".join()` na końcu — brak wady wydajnościowej.

UWAGA (ćwiczenie 09, ★ Bonus B, W7 — wprowadzana instrukcją, nie wszyta na starcie):
w ★ Bonusie B ćwiczenia 09 uczeń ma świadomie ZEPSUĆ funkcję `generate_batch_report`
poniżej: zamienić budowanie listy + `join()` na konkatenację stringów w pętli
(`report = ""; report += line + "\\n"`), zmierzyć i zobaczyć w profilu, że to NIE
jest wąskie gardło: czas raportu to `Image.open()` i I/O (1000 ID: 25,6 ms przy `+=`
i 25,5 ms przy `join()`), a CPython rozszerza string w miejscu. Wniosek: mikrooptymalizacja
bez pomiaru nie ma sensu. Zepsuta wersja NIE powinna zostać w repo.
Patrz solutions/reports_fragmenty.py — obie wersje oraz wyniki pomiaru.
"""

from __future__ import annotations

from PIL import Image

from . import images as images_module


def generate_batch_report(image_ids: list[str]) -> str:
    """Generuje raport CSV (nagłówek + jedna linia na obraz) dla listy ID.

    Kolumny: id, format, width, height, size_bytes.
    Obrazy, których nie da się otworzyć (usunięte/nieistniejące ID), trafiają
    do raportu z kolumnami błędu zamiast przerywać cały raport.
    """
    lines = ["id,format,width,height,size_bytes"]  # POPRAWNA wersja: lista + join
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
    return "\n".join(lines)  # jedno łączenie na końcu, nie w pętli
