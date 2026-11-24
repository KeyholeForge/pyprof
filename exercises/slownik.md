# Słownik pojęć — pyprof

Alfabetyczny słowniczek terminów użytych w `00-teoria.md` i czytankach
blokowych (`04a`, `06a`, `09a`, `11a`). Każde hasło: krótka definicja +
odnośnik do ćwiczenia, w którym się materializuje w praktyce. Pełne
wyjaśnienia (definicja → intuicja → po co → pomyłka) są w dokumentach
teoretycznych — tu tylko szybka ściąga.

Mapa ćwiczeń: ćw.1 = setup/Pyroscope, ćw.2 = py-spy, ćw.3 = cProfile/snakeviz,
ćw.4 = flamegrafy/tagi, ćw.5-6 = CPU, ćw.7-9 = pamięć, ćw.10-11 = GIL/asyncio,
ćw.12-14 = sieć/dysk, ćw.15 = diff/regresja, ćw.16 = finał.

---

**Areny (pymalloc)** — duże bloki pamięci (domyślnie 1 MB) żądane przez
alokator CPythona od systemu operacyjnego, dzielone na pule i bloki dla
małych obiektów. Arena wraca do OS tylko gdy CAŁA jest pusta — stąd RSS nie
zawsze spada mimo zwolnionych obiektów. → ćw. 7-9.

**Bytecode** — sekwencja niskopoziomowych instrukcji, do których CPython
kompiluje kod źródłowy Pythona przed wykonaniem; wykonywana przez pętlę
interpretera, nie bezpośrednio przez procesor. → ćw. 5-6.

**Connection pooling** — zarządzanie pulą otwartych, gotowych do reużycia
połączeń sieciowych po stronie klienta, tak by kolejne żądania nie musiały
nawiązywać nowego połączenia od zera. → ćw. 12-13.

**Continuous profiling** — ciągłe, tanie próbkowanie działającej aplikacji
(tu: Pyroscope) z możliwością porównywania profili w czasie, w
przeciwieństwie do jednorazowego profilowania ad-hoc. → ćw. 1, 4, 15.

**cProfile** — wbudowany profiler tracingowy Pythona; rejestruje obsługiwane
zdarzenia wywołań (wywołania i powroty funkcji Pythona oraz niektórych funkcji
wbudowanych, np. `min`), więc liczby wywołań są dokładne dla tego, co
rejestruje, ale ma zwykle wyższy narzut niż sampling i może zniekształcić
czasy;
wynik przeglądany m.in. przez `snakeviz`. → ćw. 3.

**Event loop** — pętla zdarzeń w `asyncio`, zwykle działająca w jednym
wątku, zarządzająca wykonaniem wielu coroutine'ów; przełącza między nimi w
punktach `await`. → ćw. 10-11.

**Fan-out** — jedno żądanie inicjujące wiele niezależnych operacji I/O;
sekwencyjny fan-out sumuje czasy, równoległy (`asyncio.gather`) ogranicza
czas do najwolniejszej operacji. → ćw. 12-13.

**Flamegraf** — wizualizacja profilu stosu wywołań: oś Y = głębokość stosu,
oś X = agregacja próbek (NIE czas), szerokość ramki = self/total time. →
ćw. 2, 4.

**fsync** — wywołanie systemowe (`os.fsync`) wymuszające fizyczny zapis
danych z bufora systemu plików na nośnik, blokujące do zakończenia; kosztowne
przy częstym wywoływaniu. → ćw. 14.

**GC (Garbage Collector) generacyjny** — mechanizm CPythona wykrywający
CYKLE referencji (których refcounting sam nie usunie); dzieli obiekty na 3
generacje (0 najmłodsza, sprawdzana najczęściej). Nie usuwa obiektów wciąż
osiągalnych przez żywe referencje (np. wpisy w cache bez limitu albo graf
zarejestrowany w globalnej szynie). → ćw. 7-9.

**gc.get_referrers(obj)** — funkcja zwracająca obiekty, które bezpośrednio
trzymają `obj`; powtarzana w górę daje łańcuch „kto trzyma" aż do zmiennej
globalnej modułu. Odpowiada na pytanie, na które nie odpowiadają tracemalloc ani
memray (te mówią, kto zaalokował). → ćw. 9.

**GIL (Global Interpreter Lock)** — blokada pozwalająca tylko jednemu
wątkowi na raz wykonywać bytecode Pythona w danym procesie; istnieje głównie
by uprościć bezpieczeństwo refcountingu. Sprawia, że `threading` nie
przyspiesza kodu CPU-bound. → ćw. 10-11.

**gil_only (Pyroscope)** — parametr klienta: True = próbkuj tylko wątki trzymające
GIL (pomija śpiące i czekające), False = także wątki czekające. W trybie wall musi
być False, inaczej `sleep` czy `fsync` znikają z profilu. → ćw. 1, 11.

**idle (próbki bezczynne)** — próbki wątków, które nic nie robią (np. czekają na
zadanie w puli: `Condition.wait`). W trybie wall potrafią stanowić większość
profilu całego serwisu; filtruj po `endpoint`. → ćw. 11.

**Interpreter loop** — główna pętla CPython (`ceval.c`), pobierająca,
dekodująca i wykonująca kolejne instrukcje bytecode; źródło narzutu
per-instrukcja w czystym kodzie Pythona. → ćw. 5-6.

**Keep-alive** — mechanizm HTTP utrzymujący połączenie TCP otwarte i
reużywane dla kolejnych żądań do tego samego hosta, zamiast zamykać je po
jednym żądaniu. → ćw. 12-13.

**Liczymy czy czekamy** — pierwsze pytanie diagnostyczne: porównaj czas zegarowy
z czasem CPU (`real` vs `user`). Równe → CPU-bound (procesy, algorytm, kod
natywny); `real` ≫ `user` → czekanie (wątki, `asyncio`, mniej połączeń). → ćw. 10-11.

**metoda związana (bound method)** — obiekt `obj.metoda`: trzyma referencję do
`obj` (`__self__`). Wstawiona do globalnej listy nasłuchujących, utrzymuje `obj`
przy życiu, dopóki nikt jej stamtąd nie usunie; `weakref.WeakMethod` jest jej
słabym odpowiednikiem. → ćw. 9.

**memray** — narzędzie do profilowania pamięci Pythona (offline `memray run`
lub podpięcie do żywego procesu `memray attach <PID>` — PID pozycyjnie, koniec
śledzenia przez `--duration N` albo `memray detach <PID>`; na macOS `sudo`);
raport `memray flamegraph --leaks` pokazuje tylko nieuwolnione (żywe) alokacje. →
ćw. 7-9.

**Off-CPU / wall-clock (profil)** — profil liczący cały upływający czas,
włącznie z oczekiwaniem na I/O (sieć, dysk, `sleep`) — w przeciwieństwie do
on-CPU. W tym kursie: `oncpu=False, gil_only=False`, wybierany RAZ przy starcie
procesu (`PYROSCOPE_WALL=1`, tag `tryb=wall`); w działającym procesie nie da się
go przełączyć. Nie widzi zawieszonej na `await` korutyny. → ćw. 11-14.

**On-CPU (profil)** — profil liczący tylko czas, w którym wątek faktycznie
wykonuje instrukcje na procesorze; NIE pokazuje czasu oczekiwania na I/O. →
ćw. 5-6, domyślny tryb Pyroscope w tym kursie (`oncpu=True, gil_only=True`, tag `tryb=cpu`).

**Pickle / serializacja (w kontekście ProcessPoolExecutor)** — konwersja
argumentów i wyników funkcji do postaci przesyłalnej między procesami;
koszt IPC przy `ProcessPoolExecutor`. → ćw. 10.

**Płaskowyż (RSS)** — poziom, na którym pamięć procesu przestaje rosnąć mimo
dalszego ruchu (np. cache z limitem); inaczej niż „powrót do wartości startowej",
którego alokator zwykle nie daje. → ćw. 8.

**ProcessPoolExecutor** — klasa z `concurrent.futures` uruchamiająca zadania
w osobnych procesach (własny GIL każdy), faktycznie równolegle na wielu
rdzeniach; koszt: serializacja danych i brak dzielonej pamięci. Obejście dla
CPU-bound wobec ograniczeń `threading`. → ćw. 10.

**Pule i bloki (pymalloc)** — podział areny pymalloc: pula (16 KiB w 64-bitowym CPythonie 3.13; 4 KiB w starszych lub 32-bitowych buildach) dzieli się
na bloki o stałym rozmiarze dla danej klasy rozmiarowej małych obiektów. →
ćw. 7-9.

**py-spy** — sampling profiler zewnętrzny (nie wymaga zmian w kodzie
aplikacji); `py-spy top`, `py-spy dump --locals`, `py-spy record -o out.svg`,
`py-spy top --gil` (tylko wątki trzymające GIL; `--gil` jest opcją
podpolecenia, `py-spy --gil top` to błąd składni). Podłączenie do działającego
procesu wymaga uprawnień: na macOS zawsze sudo, na Linuksie zwykle sudo (albo
`CAP_SYS_PTRACE`); w kontenerze Linux uruchomionym z `--cap-add SYS_PTRACE`
działa bez sudo na procesach tego samego kontenera. → ćw. 2, 10.

**pymalloc** — własny alokator pamięci CPythona zoptymalizowany pod małe
obiekty (≤512 B); żąda dużych bloków (aren) od systemu i dzieli je na
pule/bloki, zamiast wołać `malloc` przy każdej alokacji obiektu. → ćw. 7-9.

**Pyroscope** — backend continuous profilingu (Grafana Pyroscope, w Dockerze
w tym kursie); klient `pyroscope-io` konfigurowany przez
`pyroscope.configure(...)`, tagowanie bloków kodu przez `pyroscope.tag_wrapper(tags)`.
→ ćw. 1, 4, 11, 15.

**Refcounting** — licznik referencji (`ob_refcnt`) każdego obiektu Pythona;
gdy spada do zera, obiekt jest zwalniany NATYCHMIAST, deterministycznie, bez
udziału GC. Nie wykrywa cykli referencji. → ćw. 7-9.

**RSS (Resident Set Size)** — realna pamięć fizyczna aktualnie zajmowana
przez proces w RAM; nie spada natychmiast po zwolnieniu obiektów Pythona z
powodu fragmentacji aren pymalloc i zachowania alokatora systemowego. →
ćw. 7-9.

**Sampling profiler** — profiler robiący okresowe „zdjęcia" stosu wywołań
(np. co 10 ms) zamiast rejestrowania każdego wywołania; niski narzut, wynik
statystyczny (py-spy, Pyroscope). Zewnętrzny sampler, taki jak py-spy, nie
wymaga zmiany kodu, ale domyślnie na chwilę wstrzymuje proces przy każdej
próbce. Przeciwieństwo: tracing profiler. →
ćw. 1-2, 4.

**Self time / total time** — self time: czas/próbki spędzone bezpośrednio w
kodzie danej funkcji, bez funkcji przez nią wołanych. Total time: self time +
total time wszystkich funkcji wywoływanych przez nią. Kluczowe do
odróżnienia „gdzie stoi problem" od „co jest kosztowne jako całość" na
flamegrafie. → ćw. 2, 4-6.

**Semaphore (asyncio)** — mechanizm ograniczający liczbę jednocześnie
działających operacji (np. równoległych żądań HTTP) w `asyncio.gather`, by
nie przeciążyć serwera docelowego ani własnych zasobów. → ćw. 12-13.

**snakeviz** — narzędzie do wizualizacji wyników `cProfile` w przeglądarce
(interaktywny icicle/sunburst chart). → ćw. 3.

**sys.getsizeof** — funkcja zwracająca rozmiar SAMEGO obiektu (nagłówek +
dane bezpośrednie), bez rekursywnego liczenia zawartości kontenerów (np. bez
elementów listy/słownika). → ćw. 7-9.

**tracemalloc** — wbudowany moduł Pythona do śledzenia alokacji pamięci z
przypisaniem do miejsca w kodzie (plik+linia); `tracemalloc.start()`,
`tracemalloc.take_snapshot().statistics("lineno")`. → ćw. 7.

---

Powiązane dokumenty: `00-teoria.md` (primer), `04a-cpu-od-srodka.md`,
`06a-pamiec-cpythona.md`, `09a-wspolbieznosc-gil-asyncio.md`,
`11a-io-sieci-dysku.md`.

**Tracing profiler** — profiler rejestrujący obsługiwane zdarzenia (np.
wywołania i powroty funkcji) w momencie ich wystąpienia, zamiast okresowo
próbkować stos (np. `cProfile`); dokładne liczby zarejestrowanych wywołań,
ale narzut rośnie wraz
z liczbą wywołań — może zniekształcić czasy, a nawet proporcje w kodzie
drobnoziarnistym. Przeciwieństwo:
sampling profiler. → ćw. 3.
