"""solutions/filters_fragmenty.py — naprawiona wersja filtra "sepia" (ćwiczenie 05, W2).

To NIE jest plik do podmiany 1:1 — pokazuje tylko fragment do ręcznego
przeniesienia do app/images.py: zamień wywołanie `_sepia_naive` w
`apply_filter` na wersję niżej, która liczy sepię jedną operacją Pillow
zamiast pętli w czystym Pythonie. Zachowaj definicję `_sepia_naive`
w app/images.py: importują ją `solutions/profile_sepia.py` i ćwiczenie 06.

Idea naprawy: sepia to transformacja LINIOWA kanałów RGB — da się ją zapisać
jako mnożenie macierzy 3x3 (+ przesunięcie), a Pillow ma do tego wbudowaną
operację, która wykonuje pętlę po pikselach w C: `Image.convert("RGB", matrix=...)`.
Zamiast 3 000 000 iteracji interpretera Pythona (2000x1500 pikseli), cała
operacja dzieje się w kodzie natywnym. Obie wersje nadal są liniowe względem
liczby pikseli.
"""

from __future__ import annotations

from PIL import Image

# Macierz sepii w formacie oczekiwanym przez Image.convert("RGB", matrix=...):
# 12 współczynników (4 na kanał wyjściowy: mnożniki R, G, B + offset), czyli
# out_R = m[0]*R + m[1]*G + m[2]*B + m[3]
# out_G = m[4]*R + m[5]*G + m[6]*B + m[7]
# out_B = m[8]*R + m[9]*G + m[10]*B + m[11]
SEPIA_MATRIX = (
    0.393, 0.769, 0.189, 0,
    0.349, 0.686, 0.168, 0,
    0.272, 0.534, 0.131, 0,
)


def sepia_fast(img: Image.Image) -> Image.Image:
    """Zamiennik `_sepia_naive` z app/images.py — bez pętli Pythona.

    Uwaga: Image.convert z matrix samo zaokrągla każdy kanał do najbliższej
    liczby całkowitej i przycina go do 0-255, w tej samej operacji; pętla
    naiwna obcina (`int`) i ogranicza przez `min(255, ...)`. Wartość kanału
    może różnić się o 1 poziom — wizualnie równoważne, nie identyczne bit w bit.
    """
    rgb = img.convert("RGB")
    return rgb.convert("RGB", matrix=SEPIA_MATRIX)


# W app/images.py:
#
#   from PIL import Image
#
#   def apply_filter(image_id: str, name: str) -> bytes:
#       ...
#       elif name == "sepia":
#           result = img.convert("RGB", matrix=SEPIA_MATRIX)   # <-- zamiast _sepia_naive(img)
#       ...
#
# Zachowaj definicję `_sepia_naive` (importują ją ćwiczenie 06
# i solutions/profile_sepia.py, przydaje się też do porównania przed/po);
# usuń tylko jej wywołanie.
