"""solutions/gil_demo.py — demo GIL contention (ćwiczenie 10, W5).

Ten skrypt NIE jest częścią serwisu pixelforge — to samodzielny, uruchamiany
ręcznie program demonstrujący, dlaczego wątki (threading) NIE przyspieszają
obliczeń CPU-bound w CPythonie (GIL pozwala tylko jednemu wątkowi na raz
wykonywać bajtkod Pythona), a procesy (multiprocessing) — tak, bo każdy
proces ma WŁASNY interpreter i WŁASNY GIL.

Zadanie CPU-bound: liczenie liczb pierwszych w zadanym zakresie (czysty
Python, bez żadnej biblioteki C zwalniającej GIL) — analogiczne do wady W2
(naiwna sepia) w app/images.py, tylko wyizolowane do jednego pliku, żeby
można je było uruchamiać w wielu wątkach/procesach na raz i mierzyć czas.

Całkowita praca jest STAŁA (liczby pierwsze w przedziale [0, TOTAL)); tryby różnią
się tylko tym, jak ją podzielić. Przedział jest cięty na kawałki po CHUNK liczb, rozdawane workerom
na przemian (round-robin), więc każdy ma podobną ilość pracy, a suma wyników jest identyczna w każdym trybie.

Użycie:
    python solutions/gil_demo.py sequential        # baseline: 1 wątek, cała praca
    python solutions/gil_demo.py threads 4         # 4 wątki (oczekiwanie: BEZ przyspieszenia)
    python solutions/gil_demo.py processes 4       # 4 procesy (oczekiwanie: przyspieszenie)

Skrypt trwa kilka-kilkanaście sekund w trybie sequential/threads — dość długo, żeby
podpiąć py-spy z drugiego terminala (macOS wymaga sudo; Linux: --cap-add SYS_PTRACE):
    sudo py-spy dump --pid $(pgrep -f gil_demo | head -1) --locals
    sudo py-spy top --gil --pid $(pgrep -f gil_demo | head -1)
    py-spy record --gil --threads -d 5 -o profiles/ex10_gil.svg --pid <PID>
UWAGA: opcja --gil jest argumentem PODPOLECENIA (`py-spy top --gil`), nie py-spy
(`py-spy --gil top` zwraca błąd).
`py-spy top --gil` pokazuje, że w danej chwili TYLKO JEDEN wątek trzyma GIL.
W trybie `processes` każdy proces ma osobny PID i własny GIL.

Python free-threaded (3.14t, `sys._is_gil_enabled() == False`) NIE ma GIL-a — tam
wątki przyspieszają. Wyniki z ćwiczenia dotyczą zwykłego buildu z GIL-em; skrypt
wypisuje, który build uruchomiłeś.
"""

from __future__ import annotations

import sys
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

TOTAL = 5_000_000  # górna granica przedziału liczb sprawdzanych w CAŁOŚCI (stała praca)
DEFAULT_WORKERS = 4


def is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    i = 3
    while i * i <= n:
        if n % i == 0:
            return False
        i += 2
    return True


CHUNK = 50_000  # kawałki przydzielane workerom na przemian (round-robin) — wyrównuje koszt


def count_primes(offset: int, step: int) -> int:
    """Liczy liczby pierwsze w kawałkach nr offset, offset+step, ... przedziału [0, TOTAL).

    CPU-bound, czysty Python (nie zwalnia GIL-a). Kawałki zamiast reszt z dzielenia,
    bo parzyste liczby są trywialne i worker „parzysty” miałby prawie zero pracy."""
    total = 0
    for k in range(offset, TOTAL // CHUNK, step):
        total += sum(1 for n in range(k * CHUNK, (k + 1) * CHUNK) if is_prime(n))
    return total


def run_sequential(n_workers: int) -> int:
    return count_primes(0, 1)  # cała praca w jednym wątku (n_workers ignorowane)


def run_threads(n_workers: int) -> int:
    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        results = pool.map(lambda i: count_primes(i, n_workers), range(n_workers))
    return sum(results)


def run_processes(n_workers: int) -> int:
    with ProcessPoolExecutor(max_workers=n_workers) as pool:
        results = pool.map(_count_primes_star, [(i, n_workers) for i in range(n_workers)])
    return sum(results)


def _count_primes_star(args: tuple[int, int]) -> int:
    # Funkcja na poziomie modułu (nie lambda) — multiprocessing musi ją zpicklować
    # (na macOS domyślny start method to "spawn").
    return count_primes(*args)


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "sequential"
    n_workers = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_WORKERS

    gil_enabled = getattr(sys, "_is_gil_enabled", lambda: True)()
    print(f"gil_demo: mode={mode} workers={n_workers} total={TOTAL} GIL={'włączony' if gil_enabled else 'WYŁĄCZONY (free-threaded)'}")
    print(f"PID: {__import__('os').getpid()} — użyj tego PID w py-spy")

    start = time.perf_counter()
    if mode == "sequential":
        total = run_sequential(n_workers)
    elif mode == "threads":
        total = run_threads(n_workers)
    elif mode == "processes":
        total = run_processes(n_workers)
    else:
        raise SystemExit(f"Nieznany tryb: {mode!r}. Użyj: sequential | threads | processes")
    elapsed = time.perf_counter() - start

    print(f"Znalezione liczby pierwsze (suma): {total}")
    print(f"Czas: {elapsed:.2f}s")


if __name__ == "__main__":
    main()
