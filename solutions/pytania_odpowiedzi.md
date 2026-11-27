# solutions/pytania_odpowiedzi.md — klucz odpowiedzi do pytań kontrolnych

Zajrzyj tutaj PO własnej próbie odpowiedzi na pytania kontrolne z każdego
ćwiczenia (`exercises/01.md` … `16.md`).

## Ćwiczenie 1 — Setup i pierwszy flamegraf

1. Szerokość ramki = udział próbek (z wybranego okna czasu), w których dana
   funkcja występuje w tym miejscu stosu, wraz z jej wywołaniami potomnymi —
   nie czas trwania i nie liczba wywołań. Funkcja wywołana raz i trwająca
   długo może mieć węższą ramkę niż funkcja wywołana tysiące razy krótko,
   jeśli ta druga sumarycznie zjada więcej próbek. W trybie CPU kursu
   (`gil_only=True`) próbkowane są tylko wątki trzymające GIL, więc to udział
   w tych próbkach, a nie w całym czasie CPU procesu.
2. Bo `pyroscope.configure()` uruchamia klienta SDK (m.in. wątek zbierający
   próbki i wysyłający je do serwera) — próbki sprzed konfiguracji po prostu
   nie zostaną zebrane; nie ma "dogrywania" profilu wstecz. Wywołanie przy
   starcie sprawia, że profil obejmuje ruch od pierwszego requestu. Z tego
   samego powodu tryb profilera (cpu/wall) wybierasz przy starcie: ponowne
   `configure()`, gdy agent już działa, jest odrzucane (w `pyroscope-io` 1.4.0
   zwraca `False`, a tryb i tagi zostają bez zmian).
3. Profil będzie bardzo "ziarnisty" — przy 1 Hz profiler celuje średnio
   w jedną okazję do próbkowania na sekundę, więc krótkie requesty (5ms) łatwo
   zostają pominięte; przy małym ruchu udziały są zaszumione, a krótkie
   ścieżki kodu mogą w ogóle nie wystąpić. Więcej obserwacji przy
   porównywalnym obciążeniu może zmniejszyć szum losowy — potrzeba ich tylko
   znacznie więcej.

## Ćwiczenie 2 — py-spy

1. `top` to widok NA ŻYWO, odświeżany cyklicznie, agregujący próbki w
   czasie (jak `top` systemowy); `dump` to JEDNORAZOWY snapshot stosu
   wszystkich wątków Pythona w danej dokładnej chwili.
2. `tracemalloc` działa WEWNĄTRZ własnego procesu (Python instrumentuje sam
   siebie) — nie potrzebuje dostępu do pamięci INNEGO procesu. `py-spy`
   czyta pamięć CUDZEGO procesu z zewnątrz, a macOS pozwala na to tylko
   rootowi (lub podpisanemu debuggerowi) — stąd `sudo`. SIP to osobna,
   dodatkowa blokada: nawet root nie odczyta chronionych binarek
   systemowych, np. `/usr/bin/python3`. Na Linuksie podłączenie po PID zwykle
   też wymaga roota, chyba że pozwalają na to polityka ptrace systemu i Twoje
   uprawnienia (np. `CAP_SYS_PTRACE` albo `kernel.yama.ptrace_scope`
   ustawione na 0). W kontenerze Linux uruchomionym z
   `--cap-add SYS_PTRACE` py-spy działa bez `sudo` na procesach tego samego
   kontenera.
3. W fazie filtrowania loadgen losuje dla każdego żądania `grayscale`, `blur`
   i `sepia` z równym prawdopodobieństwem, więc tylko ok. 1/3 losowań to
   sepia (wcześniejsze wgrywanie obrazów to nie filtry). W tej migawce 3 z 5
   zajętych wątków roboczych miały ramkę `_sepia_naive`. To zgodne z
   hipotezą, że żądanie sepii dłużej zajmuje wątek roboczy niż pozostałe
   filtry, ale tego nie dowodzi: jedna migawka to jedna próbka. Zrób kilka
   kolejnych zrzutów w trakcie ruchu, żeby sprawdzić, czy wzorzec się
   powtarza; `py-spy top`, który domyślnie pomija wątki bezczynne, odpowiada
   na inne pytanie (gdzie padają próbki działającego kodu), a nie ile wątków
   jest zajętych. Migawka nie mówi też, ile CPU zużywa sepia — w CPythonie z
   GIL tylko jeden z tych wątków naraz może wykonywać kod Pythona (wątek ze
   statusem `idle` może np. czekać na GIL), więc wykonują się na zmianę, a nie
   równolegle — i nie podaje czasów żądań ani czasu zajęcia wątków; te zmierz
   osobno.

## Ćwiczenie 3 — cProfile + snakeviz

1. cProfile rejestruje obsługiwane zdarzenia wywołań — wywołania i powroty
   funkcji Pythona oraz niektórych funkcji wbudowanych, np. `min`
   (instrumentacja) — a to księgowanie kosztuje
   czas przy każdym zarejestrowanym wywołaniu — im więcej drobnych wywołań
   (jak 9 mln wywołań `min` w pętli pikseli), tym większy narzut. Nie rozkłada
   się on równo na wszystkie funkcje, więc zniekształcone mogą być nawet
   proporcje.
   Profiler próbkujący tylko co jakiś czas zagląda na stos, więc jego narzut
   jest zwykle dużo mniejszy. Narzut ma znaczenie zawsze, gdy odczytujesz
   czasy, a nie liczby wywołań, oraz przy profilowaniu kodu na produkcji pod
   realnym obciążeniem — tam używa się raczej profilera próbkującego
   (py-spy/Pyroscope), a czas pojedynczej funkcji mierzy się offline
   `timeit`. Liczby z mojego przebiegu:
   ten sam obraz trwał ok. 0,7 s na wywołanie w poleceniu `timeit`
   z ćwiczenia 6 i ok. 1,5 s pod cProfile — zgrubne porównanie, nie
   kontrolowany pomiar narzutu.
2. `tottime(A)` to ok. 10% czasu `A` (tylko ciało `A`, bez `B`); `cumtime(A)`
   to 100% czasu `A` (własny czas `A` plus czas w `B`). Względem całego
   profilu obie liczby zależą też od tego, co jeszcze działa poza `A`.
3. Bo skrypt włącza profiler tylko wokół wywołania `_sepia_naive`: otwarcie
   i dekodowanie JPEG oraz konwersja do RGB odbywają się przed `enable()`,
   a warstwy FastAPI/Starlette/HTTP (parsowanie requestu, middleware),
   kodowania odpowiedzi do JPEG ani zapisu w ogóle tu nie ma. W ćw. 1
   Pyroscope próbkuje stosy w działającej usłudze (tryb CPU, wątki z GIL),
   a nie tylko tę funkcję, więc ramki z tej ścieżki (obsługa requestu,
   kodowanie wyniku, middleware) mogą pojawić się na jego flamegrafie, gdy
   trafią w nie próbki — jako udział w próbkach, nie jako rozliczenie czasu
   pojedynczego requestu.

## Ćwiczenie 4 — Tagowanie i czytanie flamegrafów

1. Różne klucze się sumują (próbka ma oba tagi). Ten sam klucz z inną
   wartością: w moim pierwszym przebiegu (pyroscope-io 1.4.0; 3 × 4 s pracy
   CPU, zewnętrzny `k=outer`, wewnętrzny `k=inner`) całe ≈12,5 s CPU trafiło
   do `k=outer`, a `k=inner` dostał 0. Powtórzone przebiegi nie dały stałego
   zwycięzcy: przy tym samym zagnieżdżeniu ≈12 s trafiło do `k=inner`, a 0 do
   `k=outer` (dwukrotnie); w wariancie z dodatkową pracą poza blokiem
   wewnętrznym próbki trafiły w całości do `k=outer` (raz) albo rozdzieliły
   się między obie wartości (dwa razy). Pod którą wartością wyląduje próbka,
   nie jest określone.
   Mechanizm w SDK: pyroscope-io 1.4.0 nie trzyma stosu wartości. Wejście do
   bloku dodaje tag (wątek, klucz, wartość), a wyjście usuwa ten sam tag, więc
   wewnątrz bloku wewnętrznego wątek ma naraz `k=outer` i `k=inner`; nic nie
   przesłania wartości zewnętrznej. Którą z nich pokaże zapisany profil, tego
   powyższe przebiegi nie rozstrzygnęły.
   Wniosek: nie zagnieżdżaj tego samego klucza; do rozróżnienia warstw użyj
   różnych kluczy.
2. Dla jednej ramki odczytaj tooltip: **self** to waga próbek kończących się
   na tej ramce (funkcja wykonywała własny kod), a **total** to waga próbek
   przechodzących przez nią, wraz z jej wywołaniami podrzędnymi. Na
   flamegrafie self to ta część szerokości ramki, której nie przykrywają jej
   dzieci (ramki bezpośrednio pod nią w Pyroscope). Duży self oznacza, że duży
   udział próbkowanego CPU w tym widoku przypadł bezpośrednio na własny kod
   funkcji (jedno długie albo wiele krótkich wywołań — profil tego nie
   rozróżnia), a nie że każde wywołanie jest wolne; duży total przy małym self
   oznacza, że dzieci przykrywają prawie całą jej szerokość, więc koszt leży
   niżej. Tabela grupuje wyniki według funkcji, więc dla funkcji występującej
   w kilku miejscach stosu jej wiersz może się różnić od pojedynczej ramki.
   Wysokość ramki to tylko poziom stosu, nie miara kosztu.
3. Bo jeden proces obsługujący wiele różnych tras miesza w jednym profilu
   koszty zupełnie różnych operacji — bez tagowania nie da się odróżnić
   "ten endpoint zajmuje większość CPU" od "inny endpoint dominuje w profilu i
   przesłania pierwszy" na wspólnym, niepodzielonym flamegrafie. Tagi dzielą
   profil według tras; pokazują rozkład próbkowanego CPU, a nie latencję
   każdego żądania. Zastrzeżenie: tag jest ustawiany na
   wątek, więc dla endpointów `async def` (wspólny wątek pętli) tagi
   współbieżnych żądań się mieszają — dla `def` (synchroniczny handler działa
   na wątku roboczym z puli przez całe swoje wykonanie) są wiarygodne
   (ćwiczenie 11).

**Mini-incydent (krok 6) — czego się spodziewać.** Przeczytaj to dopiero po
zapisaniu hipotezy. U mnie profil CPU pod `endpoint=upload` pokazał
`save_bytes` z ok. 11 % próbek własnych, a obok szerszy parser multipart
(ok. 20 %). To obserwacje z mojego środowiska, nie liczby do odtworzenia, i
nie są bezpośrednio porównywalne: pierwsza to udział self jednej funkcji,
druga — szerokość ramki obejmującej wywołania podrzędne, a udział parsera pod
tagiem jest tylko przybliżony (krok 6). Aby ocenić udział ścieżki zapisu w
próbkowanym CPU, sprawdź jej Total, wraz z wywołaniami podrzędnymi, w
nieprzefiltrowanym profilu `pixelforge` z okna ruchu tylko upload. Jeśli ten
Total jest mały, profil CPU pozwala powiedzieć, że koszt CPU ścieżki uploadu
nie leży głównie w kodzie zapisu pliku. Czego nie widać: `save_bytes` woła
`os.fsync` po każdym kawałku, a gdy dysk kończy zapis, wątek czeka poza CPU —
profiler w trybie CPU (`oncpu=True`, `gil_only=True`) nie zbiera próbek tego
czekania. Próbkowanie CPU nie mówi, jak długo wątek był zablokowany na
`fsync` ani czy to oczekiwanie spowodowało zgłoszoną powolność; do tego
potrzebny jest inny pomiar — tryb wall-clock w ćwiczeniu 11 (u mnie ten sam
`save_bytes` miał tam 59 %, czyli udział próbek wall-clock, którego nie da się
porównać 1:1 z udziałami z trybu CPU) i ćwiczenie 14 o dysku.

## Ćwiczenie 5 — Naprawa naiwnej sepii

1. Operacja macierzowa Pillow wykonuje pętlę po pikselach w kodzie natywnym
   (C), bez narzutu interpretera Pythona na każdy piksel (bajtkod,
   indeksowanie przez obiekt dostępu do pikseli, tworzenie krotek i liczb,
   sprawdzanie typów) — te same współczynniki, dużo mniej „opakowania"
   wokół nich. Obie wersje nadal są O(piksele). Wyniki nie są identyczne bit
   w bit: Pillow zaokrągla każdy kanał do najbliższej liczby całkowitej i
   przycina do 0–255 w tej samej operacji, a pętla obcina przez `int`
   i ogranicza przez `min(255, …)`, więc wartość kanału może różnić się
   o 1 poziom.
2. To zmniejszyłoby OBJAW (mniej pikseli = mniej iteracji = szybciej), ale
   NIE naprawiłoby PRZYCZYNY (algorytm nadal byłby O(piksele) w czystym
   Pythonie) — dla oryginalnego rozmiaru obrazu problem by wrócił. Zmieniłoby
   też wynik (mniejszy obraz), więc w ogóle nie jest naprawą.
3. Gdyby otagowane żądania grayscale zużywały więcej próbkowanego CPU
   (z GIL), `filter=grayscale` mógłby mieć największy Total korzenia
   w widoku `endpoint=filter`. Posortuj tabelę po Self w widoku
   `filter=grayscale`, żeby zobaczyć, gdzie trafia ta waga — np. własna pętla
   w Pythonie albo nieoptymalna konwersja kolorów wywoływana z gałęzi
   `grayscale` w `apply_filter`; funkcja o największym Self całego endpointu
   nie musi pochodzić z tego filtra. Samo wolne żądanie nie przesądza żadnego
   z tych rankingów i nie zakładaj z góry, że wszystkie filtry mają tę samą
   klasę wady. Gdyby wolna część była kodem natywnym zwalniającym GIL, ten
   profil CPU (`gil_only=True`) mógłby jej prawie nie pokazać — zmierz czasy
   żądań (krok 3) i użyj profilu wall-clock (ćwiczenie 11).
