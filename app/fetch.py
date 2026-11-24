"""Pobieranie obrazów z URL (serwis `origin` z docker-compose lub inny host).

Ten moduł DZIAŁA od startu, ale celowo zawiera wadę sieciową W3 (TCP),
w dwóch częściach:
  - W3a (ćwiczenia 12-13): nowy httpx.AsyncClient() przy każdym wywołaniu.
  - W3b (ćwiczenie 13): fetch-batch pobiera URL-e sekwencyjnie, nie równolegle.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from urllib.parse import urlparse

import httpx

from . import config, storage


async def fetch_one(url: str) -> dict:
    """Pobiera pojedynczy obraz spod `url` i zapisuje go do lokalnego storage.

    WADA SIECIOWA (W3a, ćwiczenia 12-13): tworzymy NOWEGO `httpx.AsyncClient()`
    (menedżer kontekstu `async with`) przy KAŻDYM wywołaniu tej funkcji, zamiast
    reużywać jednej sesji z poolem połączeń. Skutki (pomiar, origin z opóźnieniem
    25 ms): każde żądanie otwiera nowe połączenie TCP (203 połączenia na 203 żądania
    w `/nginx_status`), płaci za budowę klienta i SSLContext (~2,3 ms CPU) i trwa
    ok. 2x dłużej niż ze współdzielonym klientem (72 ms vs 34 ms).
    Naprawiona wersja (jeden `httpx.AsyncClient` w `app.state`, przekazywany do
    `fetch_one(client, url)`): solutions/fetch_fragmenty.py.
    """
    async with httpx.AsyncClient() as client:  # W3a: nowy klient za każdym razem
        resp = await client.get(url, timeout=10.0)
        resp.raise_for_status()
        data = resp.content

    image_id = uuid.uuid4().hex
    suffix = Path(urlparse(url).path).suffix or ".jpg"
    dest = config.UPLOAD_DIR / f"{image_id}{suffix}"
    storage.save_bytes(dest, data)
    return {"id": image_id, "url": url, "size": len(data)}


async def fetch_batch(urls: list[str]) -> list[dict]:
    """Pobiera listę URL-i i zwraca listę wyników (sukces lub błąd per URL).

    WADA SIECIOWA (W3b, ćwiczenie 13): URL-e są pobierane SEKWENCYJNIE w pętli
    `for` — każdy `await fetch_one(url)` czeka na zakończenie poprzedniego.
    Czas rośnie liniowo z liczbą URL-i (8 URL-i przy opóźnieniu origin 25 ms:
    ok. 270 ms sekwencyjnie wobec ok. 42 ms równolegle). Czekania `await` nie widać
    w profilu próbkującym (brak stosu zawieszonej korutyny) — mierz czas.
    Naprawiona wersja (równoległe pobieranie przez `asyncio.gather` na
    współdzielonym kliencie): solutions/fetch_fragmenty.py.
    """
    results: list[dict] = []
    for url in urls:  # W3b: sekwencyjnie — powinno być asyncio.gather(*...)
        try:
            results.append(await fetch_one(url))
        except httpx.HTTPError as exc:
            results.append({"url": url, "error": str(exc)})
    return results
