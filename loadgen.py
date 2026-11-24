#!/usr/bin/env python3
"""loadgen.py — generator ruchu dla kursu pyprof (serwis pixelforge, port 8040).

Symuluje realny ruch użytkowników, żeby dać profilowi (Pyroscope/py-spy/
memray) coś do pokazania: uploady, miniatury, filtry (w tym naiwny W2),
pobieranie z serwisu `origin` (pojedyncze i wsadowe — W3), raporty wsadowe.

Obrazy do miniatur/filtrów/raportów są wgrywane JEDNORAZOWO na starcie
(pula ID, `--pool`); dalej loadgen odpytuje tylko te ID. Upload w trakcie
ruchu robi wyłącznie scenariusz `upload` (i `mixed`, w małej części).

Wymaga uruchomionej aplikacji pixelforge (`uvicorn app.main:app --port 8040`)
i — dla scenariusza `fetch` — serwisu `origin` z docker-compose (port 8041).

Przykłady:
    python loadgen.py --duration 30 --concurrency 5
    python loadgen.py --scenario thumbnails --duration 15 --concurrency 10
    python loadgen.py --scenario fetch --duration 20 --concurrency 3
    python loadgen.py --scenario upload --duration 15 --concurrency 4
"""

from __future__ import annotations

import argparse
import asyncio
import random
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parent
CORPUS_DIR = REPO_ROOT / "data" / "corpus"

DEFAULT_BASE_URL = "http://127.0.0.1:8040"
DEFAULT_ORIGIN_URL = "http://127.0.0.1:8041"

FILTERS = ("grayscale", "blur", "sepia")
# Rozmiary miniatur z przedziału (nie czteroelementowej listy): duża przestrzeń
# kluczy (id, size) sprawia, że cache miniatur (W1) rośnie przez cały bieg,
# zamiast osiągnąć płaskowyż po kilkuset żądaniach.
THUMBNAIL_SIZE_RANGE = (32, 384)
POOL_DEFAULT = 100

SCENARIOS = ("thumbnails", "filters", "fetch", "reports", "upload", "pipeline", "mixed", "final")

# Wagi scenariusza `final` (ćwiczenie 16): więcej miniatur i pobrań, mniej raportów —
# każda wada ma wystarczająco dużo ruchu, żeby dało się ją odróżnić w pomiarze łącznym.
FINAL_WEIGHTS = {"thumbnails": 40, "filters": 15, "fetch": 25, "reports": 5, "upload": 15}


@dataclass
class Stats:
    requests: int = 0
    errors: int = 0
    by_scenario: dict[str, int] = field(default_factory=dict)
    errors_by_scenario: dict[str, int] = field(default_factory=dict)
    latencies_ms: list[float] = field(default_factory=list)

    def record(self, scenario: str, ok: bool, elapsed_ms: float) -> None:
        self.requests += 1
        self.by_scenario[scenario] = self.by_scenario.get(scenario, 0) + 1
        self.latencies_ms.append(elapsed_ms)
        if not ok:
            self.errors += 1
            self.errors_by_scenario[scenario] = self.errors_by_scenario.get(scenario, 0) + 1


class Corpus:
    """Lista plików z lokalnego korpusu (data/corpus/) do uploadu."""

    def __init__(self, corpus_dir: Path) -> None:
        self.files = sorted(corpus_dir.glob("*.jpg"))
        if not self.files:
            raise SystemExit(
                f"Brak obrazów w {corpus_dir} — uruchom najpierw "
                f"`python scripts/gen_corpus.py`."
            )

    def random_file(self) -> Path:
        return random.choice(self.files)


class OriginCatalog:
    """Lista URL-i obrazów serwowanych przez `origin` (docker-compose, :8041)."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._urls: list[str] | None = None

    async def urls(self, client: httpx.AsyncClient) -> list[str]:
        if self._urls is None:
            resp = await client.get(f"{self.base_url}/", timeout=10.0)
            resp.raise_for_status()
            names = re.findall(r'href="([^"?/]+\.jpg)"', resp.text)
            self._urls = [f"{self.base_url}/{name}" for name in names]
            if not self._urls:
                raise SystemExit(
                    f"Serwis origin ({self.base_url}) nie zwrócił żadnych .jpg — "
                    f"czy docker compose up -d origin wystartował i data/origin_images "
                    f"ma zawartość?"
                )
        return self._urls

    async def random_urls(self, client: httpx.AsyncClient, n: int) -> list[str]:
        pool = await self.urls(client)
        return random.sample(pool, k=min(n, len(pool)))


async def upload_random_image(client: httpx.AsyncClient, base_url: str, corpus: Corpus) -> str:
    path = corpus.random_file()
    with open(path, "rb") as f:
        files = {"file": (path.name, f, "image/jpeg")}
        resp = await client.post(f"{base_url}/images", files=files, timeout=30.0)
    resp.raise_for_status()
    return resp.json()["id"]


async def run_upload(client: httpx.AsyncClient, base_url: str, corpus: Corpus) -> None:
    await upload_random_image(client, base_url, corpus)


async def run_thumbnails(client: httpx.AsyncClient, base_url: str, pool: list[str]) -> None:
    image_id = random.choice(pool)
    size = random.randint(*THUMBNAIL_SIZE_RANGE)
    resp = await client.get(f"{base_url}/images/{image_id}/thumbnail", params={"size": size}, timeout=30.0)
    resp.raise_for_status()


async def run_filters(client: httpx.AsyncClient, base_url: str, pool: list[str]) -> None:
    image_id = random.choice(pool)
    name = random.choice(FILTERS)
    resp = await client.get(f"{base_url}/images/{image_id}/filter/{name}", timeout=60.0)
    resp.raise_for_status()


async def run_pipeline(client: httpx.AsyncClient, base_url: str, pool: list[str]) -> None:
    # Za każdym razem DOKŁADNIE to samo żądanie (ten sam obraz, ten sam preset):
    # wzrost pamięci przy powtarzaniu identycznego żądania odróżnia wyciek od cache.
    resp = await client.get(f"{base_url}/images/{pool[0]}/pipeline/szkic", timeout=30.0)
    resp.raise_for_status()


async def run_fetch(client: httpx.AsyncClient, base_url: str, origin: OriginCatalog) -> None:
    if random.random() < 0.5:
        urls = await origin.random_urls(client, 1)
        resp = await client.post(f"{base_url}/images/fetch", json={"url": urls[0]}, timeout=30.0)
        resp.raise_for_status()
    else:
        urls = await origin.random_urls(client, random.randint(3, 6))
        resp = await client.post(f"{base_url}/images/fetch-batch", json={"urls": urls}, timeout=60.0)
        resp.raise_for_status()


async def run_reports(client: httpx.AsyncClient, base_url: str, pool: list[str], report_ids: int = 0) -> None:
    if report_ids:  # stała, duża liczba ID w raporcie (z powtórzeniami z puli)
        ids = random.choices(pool, k=report_ids)
    else:
        ids = random.sample(pool, k=min(len(pool), random.randint(3, 10)))
    resp = await client.post(f"{base_url}/reports/batch", json={"ids": ids}, timeout=60.0)
    resp.raise_for_status()


async def build_pool(base_url: str, corpus: Corpus, size: int) -> list[str]:
    """Wgrywa `size` losowych obrazów z korpusu (raz) i zwraca ich ID."""
    async with httpx.AsyncClient() as client:
        return [await upload_random_image(client, base_url, corpus) for _ in range(size)]


async def worker(
    worker_id: int,
    scenario: str,
    base_url: str,
    origin_url: str,
    corpus: Corpus,
    origin: OriginCatalog,
    pool: list[str],
    stats: Stats,
    deadline: float,
    report_ids: int = 0,
    max_requests: int = 0,
) -> None:
    async with httpx.AsyncClient() as client:
        while time.monotonic() < deadline and not (max_requests and stats.requests >= max_requests):
            if scenario == "final":
                chosen = random.choices(list(FINAL_WEIGHTS), weights=list(FINAL_WEIGHTS.values()))[0]
            else:
                chosen = scenario if scenario != "mixed" else random.choice(
                ("thumbnails", "filters", "fetch", "reports", "upload")
            )
            start = time.monotonic()
            ok = True
            try:
                if chosen == "thumbnails":
                    await run_thumbnails(client, base_url, pool)
                elif chosen == "filters":
                    await run_filters(client, base_url, pool)
                elif chosen == "fetch":
                    await run_fetch(client, base_url, origin)
                elif chosen == "pipeline":
                    await run_pipeline(client, base_url, pool)
                elif chosen == "upload":
                    await run_upload(client, base_url, corpus)
                elif chosen == "reports":
                    await run_reports(client, base_url, pool, report_ids)
                else:
                    raise ValueError(f"Nieznany scenariusz: {chosen}")
            except Exception as exc:  # noqa: BLE001 — loadgen ma przeżyć błędy pojedynczych requestów
                ok = False
                print(f"[worker {worker_id}] {chosen} error: {exc}", file=sys.stderr)
            elapsed_ms = (time.monotonic() - start) * 1000
            stats.record(chosen, ok, elapsed_ms)


async def main_async(args: argparse.Namespace) -> None:
    corpus = Corpus(CORPUS_DIR)
    origin = OriginCatalog(args.origin_url)
    stats = Stats()
    pool: list[str] = []
    if args.scenario in ("thumbnails", "filters", "reports", "pipeline", "mixed", "final"):
        t0 = time.monotonic()
        pool = await build_pool(args.base_url, corpus, args.pool)
        print(f"loadgen: pula {len(pool)} ID wgrana w {time.monotonic() - t0:.1f}s")

    deadline = time.monotonic() + args.duration
    print(
        f"loadgen: scenariusz={args.scenario} concurrency={args.concurrency} "
        f"duration={args.duration}s target={args.base_url}"
    )

    workers = [
        worker(i, args.scenario, args.base_url, args.origin_url, corpus, origin, pool, stats, deadline, args.report_ids, args.requests)
        for i in range(args.concurrency)
    ]
    await asyncio.gather(*workers)

    print()
    print("=== Podsumowanie loadgenu ===")
    print(f"  Requesty: {stats.requests}  Błędy: {stats.errors}")
    if stats.latencies_ms:
        latencies = sorted(stats.latencies_ms)
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95) - 1] if len(latencies) > 1 else latencies[0]
        print(f"  Latencja p50={p50:.1f}ms p95={p95:.1f}ms max={latencies[-1]:.1f}ms")
    print("  Per scenariusz:")
    for name in sorted(stats.by_scenario):
        errs = stats.errors_by_scenario.get(name, 0)
        print(f"    {name}: {stats.by_scenario[name]} (błędy: {errs})")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-c", "--concurrency", type=int, default=5, help="liczba równoległych workerów (domyślnie 5)")
    parser.add_argument("--duration", type=float, default=30.0, help="czas trwania w sekundach (domyślnie 30)")
    parser.add_argument("--scenario", choices=SCENARIOS, default="mixed", help="scenariusz ruchu (domyślnie mixed)")
    parser.add_argument("--pool", type=int, default=POOL_DEFAULT, help=f"ile obrazów wgrać raz na starcie jako pulę ID (domyślnie {POOL_DEFAULT})")
    parser.add_argument("--report-ids", type=int, default=0, help="stała liczba ID w raporcie wsadowym (domyślnie losowo 3-10)")
    parser.add_argument("--requests", type=int, default=0, help="górny limit liczby żądań w biegu (domyślnie bez limitu; bieg kończy się też po --duration)")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help=f"adres pixelforge (domyślnie {DEFAULT_BASE_URL})")
    parser.add_argument("--origin-url", default=DEFAULT_ORIGIN_URL, help=f"adres serwisu origin (domyślnie {DEFAULT_ORIGIN_URL})")
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        print("\nPrzerwano.")


if __name__ == "__main__":
    main()
