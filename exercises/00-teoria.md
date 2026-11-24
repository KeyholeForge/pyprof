# 00. Teoria: jak działa Python od środka i jak się go profiluje

Duży primer, nie ćwiczenie — bez zadań i kryteriów „done". Cel: zbudować mapę
pojęć, zanim wejdziesz w ćwiczenia 1-16. Każde pojęcie w schemacie:

> **Definicja** → **Intuicja/analogia** → **Po co to** → **Częsta pomyłka**

Wracaj tu, gdy coś przestanie się spinać. Krótkie definicje wszystkich terminów
są w `slownik.md`. Przed blokami tematycznymi czekają jeszcze węższe czytanki:
`04a-cpu-od-srodka.md`, `06a-pamiec-cpythona.md`, `09a-wspolbieznosc-gil-asyncio.md`,
`11a-io-sieci-dysku.md` — ten dokument daje wspólny fundament pod wszystkie
cztery.

Kontekst: przez cały kurs profilujesz jedną aplikację — **pixelforge**, serwis
FastAPI do przetwarzania obrazów (upload, miniatury, filtry, pobieranie z URL,
raporty wsadowe). Ma celowo wszyte wady wydajnościowe, które kolejne ćwiczenia
każą Ci znaleźć profilerem, a potem naprawić. Przykłady w tym dokumencie
odwołują się do realnych modułów tej aplikacji (`app/images.py`,
`app/fetch.py`, `app/storage.py`, `app/reports.py`), żebyś od razu widział,
gdzie teoria styka się z kodem, który będziesz uruchamiał.

---

## Bytecode i pętla interpretera CPython

**Definicja.** CPython (implementacja Pythona, której używasz) nie wykonuje
plików `.py` bezpośrednio. Najpierw kompiluje kod źródłowy do **bytecode** —
sekwencji prostych instrukcji niskiego poziomu (np. `LOAD_FAST`, `CALL`,
`BINARY_OP`; dokładne nazwy zmieniają się między wersjami — przy prostym
odczycie zmiennej lokalnej CPython 3.14 często pokazuje `LOAD_FAST_BORROW` tam,
gdzie 3.11–3.13 pokazują `LOAD_FAST`),
zapisanych w obiektach `code`. Bytecode importowanych modułów może być
zapisany w plikach `.pyc` w `__pycache__`. Sercem CPythona jest **pętla
interpretera** (interpreter loop) w `ceval.c`, która — w uproszczeniu — w kółko:
pobiera kolejną instrukcję bytecode, dekoduje ją, wykonuje odpowiadającą jej
operację w C, i wraca po następną. Od 3.11 pętla dodatkowo specjalizuje gorące
instrukcje pod napotkane typy (interpreter adaptacyjny), co zmniejsza, ale nie
usuwa narzutu na instrukcję.

**Intuicja.** To jak tłumacz symultaniczny, który nie zna z góry całej mowy —
dostaje ją zdanie po zdaniu (instrukcja po instrukcji) i tłumaczy na bieżąco
na „język maszyny" (wywołania funkcji C). Każde tłumaczone zdanie kosztuje
pewien narzut samego tłumaczenia — stąd Python jest wolniejszy per-operację niż
język kompilowany bezpośrednio do kodu maszynowego.

**Po co to.** Rozumienie, że Python wykonuje się przez interpretację bytecode,
tłumaczy dwie rzeczy kluczowe dla profilowania: (1) profiler widzi **ramki
stosu wywołań funkcji Pythona** (stack frames), nie pojedyncze instrukcje
procesora — flamegraf pokazuje „jesteś w funkcji `_sepia_naive`, która woła
`Image.load`", a nie „jesteś w instrukcji `MOV`". (2) narzut interpretacji
jest ponoszony przy wykonywaniu instrukcji, a jego koszt zależy od operacji —
dlatego pętla `for` w czystym
Pythonie, wykonująca miliony prostych operacji, jest zwykle dużo wolniejsza niż
równoważna praca zaimplementowana w bibliotece napisanej w C (jak Pillow czy
numpy), która robi całą pracę w JEDNYM wywołaniu z poziomu Pythona, a
milionową pętlę wykonuje już poza interpreterem. To dokładnie mechanizm wady
W2 w `app/images.py::_sepia_naive` — podwójna pętla `for y / for x` nad
pikselami w Pythonie zamiast oddania pracy na pikselach kodowi C Pillow.
Więcej o tym w `04a-cpu-od-srodka.md`.

**Częsta pomyłka.** „Flamegraf pokazuje, która LINIA kodu C/maszynowego jest
wolna, więc mogę zoptymalizować na poziomie procesora." Nie — standardowe
profilery Pythona używane tutaj (py-spy, cProfile, Pyroscope, w domyślnej
konfiguracji kursu) operują na poziomie **ramek
funkcji Pythona**, nie linii asemblera. Widzisz, ile czasu/próbek spędzono
W FUNKCJI (i opcjonalnie na której linii Pythona), a nie w której instrukcji
procesora. W większości przypadków to wystarcza — problem wydajnościowy w kodzie
aplikacyjnym zwykle da się zlokalizować na poziomie funkcji.

---

## GIL (Global Interpreter Lock)

**Definicja.** W standardowym CPythonie z GIL, używanym w kursie, tylko jeden
wątek naraz wykonuje bytecode Pythona w obrębie jednego interpretera.

**Intuicja.** Wyobraź sobie kuchnię z jednym nożem. Kucharze kroją na zmianę,
mogą jednocześnie czekać na piekarnik albo robić coś, do czego nóż nie jest
potrzebny. Rozszerzenia natywne zwalniające GIL mogą liczyć równolegle.

**Po co to.** GIL upraszcza dostęp do współdzielonego stanu interpretera,
w tym do liczników referencji. CPython w wersji free-threaded zarządza tym
stanem m.in. za pomocą osobnych liczników lokalnych i współdzielonych. Kurs
używa standardowego buildu. `py-spy top --gil --pid <PID>` filtruje obserwacje
do wątków posiadających GIL (podłączenie do działającego procesu wymaga
odpowiednich uprawnień, zob. ćwiczenie 2). Pomija oczekujące wątki oraz pracę
natywną bez GIL. Sam filtr nie mierzy czasu oczekiwania na blokadę.

**Częsta pomyłka.** Dodanie wątków w celu przyspieszenia pętli po pikselach
w `_sepia_naive`. W interpreterze kursu wątki wykonują bytecode na zmianę.
Mogą nakładać na siebie oczekiwanie na blokujące I/O — gdy jeden wątek czeka na
plik albo gniazdo, inny może działać — a kod natywny może liczyć równolegle po
zwolnieniu GIL. Alternatywę z pulą procesów opisuje
`09a-wspolbieznosc-gil-asyncio.md`.

---

## Refcounting i Garbage Collector generacyjny

**Definicja.** CPython zarządza pamięcią dwuwarstwowo. Warstwa pierwsza:
**refcounting** — każdy obiekt Pythona ma licznik silnych referencji
(`ob_refcnt`).
Gdy tworzysz referencję do obiektu (przypisanie, dodanie do listy/słownika),
licznik rośnie; gdy referencja znika (koniec zasięgu, `del`, nadpisanie
zmiennej), licznik maleje. (To model myślowy; od 3.12 obiekty „nieśmiertelne",
takie jak `None`, mają stały licznik, a interpreter wewnętrznie pomija część
aktualizacji licznika.) Gdy licznik spada do zera, obiekt jest dealokowany
**natychmiast**, deterministycznie — bez czekania na jakikolwiek „przebieg"
odśmiecacza (jego pamięć wraca do alokatora, niekoniecznie do systemu
operacyjnego). Warstwa druga: **Garbage Collector (GC) generacyjny** — dodatkowy
mechanizm, który wyłapuje **cykle referencji** (obiekt A wskazuje na B, B
wskazuje z powrotem na A — refcounting nigdy nie sprowadzi ich liczników do
zera samodzielnie, mimo że nic z zewnątrz już ich nie używa). GC śledzi obiekty
mogące uczestniczyć w cyklach, np. listy, słowniki, instancje klas i wiele
innych kontenerów — nie np. inty czy napisy. W standardowym buildzie wersji
kursu (CPython 3.11–3.13 i 3.14.5+) dzieli je na 3 generacje (0 =
najmłodsze/najczęściej sprawdzane, 2 = najstarsze/najrzadziej sprawdzane).
Nowo śledzone obiekty zaczynają w generacji 0. Jeśli przeżyją zbiórkę, mogą
przejść do starszej generacji; obiekty w najstarszej pozostają w niej. Młodsze
generacje są skanowane częściej, bo statystycznie większość obiektów umiera
młodo (hipoteza pokoleniowa). (CPython 3.14.0–3.14.4 miał inkrementalny GC bez
środkowej generacji; 3.14.5 przywrócił zachowanie z 3.13.)

**Intuicja.** Refcounting to jak liczenie osób trzymających parasol wspólnie —
gdy ostatnia osoba puszcza, parasol od razu spada (obiekt zwolniony
natychmiast). GC to osobna ekipa sprzątająca, która co jakiś czas obchodzi
pokój i szuka grupek osób trzymających się nawzajem za ręce w kółko, tak że
żadna z nich formalnie nikogo „nie puszcza", a mimo to cała grupka jest
odcięta od reszty pokoju (nieosiągalna z zewnątrz) — refcounting tego sam nie
wykryje, bo liczniki nigdy nie spadają do zera.

**Po co to.** Rozróżnienie „refcount=0 → zwolnienie natychmiastowe" vs „cykl →
wymaga GC" tłumaczy, dlaczego niektóre wycieki pamięci w Pythonie są
subtelne: kod może wyglądać, jakby „nic nie trzymał" obiektu, a mimo to
obiekt żyje, bo jest gdzieś referencja o której nie pomyślałeś (np. w
kontenerze globalnym). To bezpośrednio dotyczy `app/images.py::THUMBNAIL_CACHE`
(wada W1, ćwiczenie 08): każdy wpis w tym słowniku to żywa referencja do
danych miniatury — refcount tych bajtów NIGDY nie spadnie do zera, dopóki
klucz `(image_id, size)` siedzi w słowniku, bo sam słownik jest globalny
i żyje przez cały czas trwania procesu. To nie jest cykl (GC by tu nie
pomógł) — to zwyczajna, żywa referencja, której nikt nie usuwa. Więcej w
`06a-pamiec-cpythona.md`. Prawdziwy wyciek tego samego rodzaju (wada W1b,
ćwiczenie 09): obiekt budowany przy każdym żądaniu, który w konstruktorze
rejestruje swoją metodę (`EVENTS.subscribe(self.on_progress)`) w globalnej szynie
zdarzeń — metoda związana trzyma `self`, szyna trzyma metodę, moduł trzyma
szynę. Kto trzyma obiekt, sprawdzisz przez `gc.get_referrers` (zwraca
bezpośrednich trzymających spośród kontenerów śledzonych przez GC — to pomoc
w debugowaniu, nie pełny graf referencji); typowe źródła
takich wycieków (rejestry i nasłuchujący, domknięcia w globalnych listach,
`lru_cache` na metodzie, handlery logowania dodawane per żądanie) są w
`06a-pamiec-cpythona.md`.

**Częsta pomyłka.** „W Pythonie nie ma wycieków pamięci, bo jest GC." GC
odzyskuje tylko obiekty, które przestały być osiągalne — grupy trzymane razem
wyłącznie przez cykle referencji (i to, co trzymają tylko te grupy). Nie usuwa
obiektów, do których wciąż istnieje żywa referencja (jak wpis w cache'u, który
rośnie bez ograniczeń). „Wyciek pamięci" w kodzie Pythona najczęściej oznacza:
„ktoś gdzieś trzyma referencję dłużej niż powinien", nie: „GC nie działa"
(innym możliwym źródłem wzrostu są alokacje natywne w rozszerzeniach C).

---

## Alokator pamięci CPythona: pymalloc, areny, pule

**Definicja.** Gdy obiekt Pythona jest tworzony, CPython nie prosi systemu
operacyjnego o pamięć za każdym razem — używa własnego alokatora, **pymalloc**,
zoptymalizowanego pod małe żądania alokacji (do 512 bajtów każde, czyli większość
małych obiektów: int, krótkie str, krotki, małe listy). Pymalloc żąda od OS
dużych bloków — **aren** (domyślnie 1 MiB w 64-bitowych buildach wersji kursu,
3.11–3.14) — a każdą arenę dzieli na **pule** (pools, 16 KiB; starsze lub
32-bitowe buildy: areny 256 KiB i pule 4 KiB), a każdą pulę na **bloki**
o stałym rozmiarze dla danej klasy rozmiarowej. Gdy Python „zwalnia" mały
obiekt (refcount spada do zera), jego blok wraca do swojej puli pymalloc — ale
arena może zostać zwrócona systemowi operacyjnemu (co realnie może zmniejszyć
RSS procesu) dopiero wtedy, gdy CAŁA jest pusta. Większe żądania (> 512 B) —
jak surowe bajty obrazu w `THUMBNAIL_CACHE` — trafiają do alokatora
systemowego (`malloc`); oddanie pamięci temu alokatorowi nie musi zmniejszyć
RSS.

**Intuicja.** Wyobraź sobie regał z szufladkami zamawiany hurtowo (arena),
podzielony na przegródki jednego rozmiaru (pula), z których każda mieści
konkretny typ przedmiotu (bloki). Gdy wyjmujesz przedmiot (zwalniasz obiekt),
przegródka staje się pusta i gotowa na następny przedmiot TEGO SAMEGO
rozmiaru — ale cały regał (arena) trafia z powrotem do magazynu (OS) tylko
gdy WSZYSTKIE przegródki na nim są puste. Jeśli w jednej przegródce z tysiąca
wciąż siedzi jeden przedmiot, cały regał zostaje zajęty.

**Po co to.** RSS obejmuje rezydentne strony procesu, w tym pamięć dostępną
do ponownego użycia przez alokator. Żywe bloki mogą utrzymać arenę pymalloc
w pamięci. Pustą arenę utworzoną przez `mmap` można odmapować. Pamięć oddana
do `malloc` może pozostać w rezerwie tego alokatora. W ćwiczeniu 08 sprawdź,
czy przy porównywalnym, stałym obciążeniu wzrost pamięci się zatrzymuje.
Liczbę wpisów w cache sprawdź bezpośrednio.

**Częsta pomyłka.** Traktowanie RSS jako rozmiaru żywych obiektów Pythona.
`tracemalloc` raportuje rozmiar i liczbę aktualnie śledzonych bloków według
miejsca alokacji. Bloki nie muszą odpowiadać wpisom w cache jeden do jednego.
Alokacje natywne poza mechanizmem śledzenia mogą być pominięte.
`sys.getsizeof()` podaje płytki rozmiar obiektu, bez obiektów, do których
ten się odwołuje. Zobacz ćwiczenie 07 i `06a-pamiec-cpythona.md`.

---

## Profiler samplujący (sampling) vs profiler śledzący (tracing)

**Definicja.** Profiler deterministyczny, taki jak `cProfile`, obserwuje
zdarzenia wywołań i powrotów oraz agreguje liczniki i czasy według funkcji.
Liczniki dotyczą zaobserwowanych wywołań, a czasy pochodzą z wykonania pod
profilerem. Profiler samplujący, taki jak `py-spy`, okresowo pobiera stosy.
Udział próbek szacuje, gdzie program spędza czas w wybranym trybie pomiaru.

**Intuicja.** Tracing przypomina rejestrowanie każdego przejścia przez drzwi
i podliczanie wpisów. Sampling przypomina okresowe fotografowanie pokoju,
by oszacować, gdzie ludzie spędzają czas.

**Po co to.** Używaj `py-spy` lub Pyroscope do szukania dominujących kosztów
pod obciążeniem (ćwiczenia 1–2 i 4), a `cProfile` z SnakeViz do liczników
wywołań funkcji i czasów skumulowanych w krótkim przebiegu (ćwiczenie 3).
W `pstats` `tottime` nie obejmuje czasu podwywołań, a `cumtime` go obejmuje;
domyślnie to pomiary czasu upływającego, nie czasu CPU.
Obsługa zdarzeń może zawyżać względny koszt kodu z wieloma drobnymi
wywołaniami. Próbkowanie zwykle mniej zaburza taki przebieg. Sprawdź narzut
pod reprezentatywnym obciążeniem.

**Częsta pomyłka.** Zakładanie, że jedna metoda zawsze jest dokładniejsza.
Krótki sampling może pominąć część pracy. Tracing może zniekształcić czasy
przez własny narzut.

---

## On-CPU, off-CPU i wall-clock i granice profilera

**Definicja.** **Czas on-CPU** to czas, w którym wątek FAKTYCZNIE wykonuje
instrukcje na procesorze. **Czas off-CPU** to czas, w którym wątek nie wykonuje
się na CPU — jest zablokowany (czeka na I/O, blokadę, zegar) albo gotowy do
działania, ale nieprzydzielony do procesora. Idealny **profil on-CPU** liczy
tylko czas on-CPU. **Profil wall-clock** liczy CAŁKOWITY upływający czas,
włącznie z czasem oczekiwania — wątek zablokowany na `socket.recv()` czy
`time.sleep()` pojawia się w profilu wall-clock jako „spędzający czas" w tym
wywołaniu, mimo że procesor w tym czasie robi coś zupełnie innego (albo nic).
Profil wall-clock obejmuje więc czas on-CPU oraz off-CPU; nie jest tym samym co
czysty profil off-CPU.

Profiler samplujący taki jak ten w kliencie Pyroscope nie dostaje tych czasów od
planisty systemu operacyjnego — okresowo odczytuje stosy wątków i decyduje,
które próbki zachować. W kliencie Pyroscope (`pyroscope-io` 1.4.0, domyślna
implementacja oparta na py-spy) decydują o tym dwa filtry: `oncpu` (True =
odrzuca próbki wątków, które sampler uznał za bezczynne — to heurystyka, nie
rozliczenie czasu przez planistę; False = je zachowuje) i `gil_only` (True =
tylko wątki trzymające GIL; False = bez filtra GIL). Kurs używa dwóch presetów:
**cpu** = `oncpu=True, gil_only=True` (przybliżenie pracy Pythona na CPU; praca
natywna po zwolnieniu GIL jest pomijana) i **wall** = `oncpu=False,
gil_only=False` (oba filtry wyłączone, więc zachowane są też wątki czekające).
W trybie wall próbki kilku wątków się sumują, więc ich suma nie jest czasem
trwania żadnego pojedynczego żądania. Preset wybierasz **raz, przy starcie
procesu**
(`PYROSCOPE_WALL=1`, po zaimplementowaniu ćwiczenia 11) i oznaczasz tagiem
`tryb=cpu|wall`; ponowne `configure()` w działającym procesie jest odrzucane
(w 1.4.0 zwraca `False`) i nie zmienia ani trybu, ani tagów, więc zmiana trybu
= restart.

**Intuicja.** On-CPU to stoper mierzący tylko czas, w którym kucharz faktycznie
kroi warzywa. Wall-clock to stoper mierzący od momentu, gdy kucharz zaczyna
przepis, do momentu gdy go kończy — łącznie z czasem stania przy piekarniku.

**Po co to.** To rozróżnienie rozstrzyga, czy dany problem w ogóle zobaczysz.
W ćwiczeniu 11 dodajesz do endpointu `async def` sztuczne `time.sleep(2)`
(blokuje pętlę zdarzeń). W opisanym tam kontrolowanym przebiegu, z filtrem
`endpoint=fetch`, sampler w presecie cpu zarejestrował co najwyżej kilka próbek
kodu wokół oczekiwania i żadnej próbki własnej `fetch_image` (wątek śpi, nie
liczy), a w presecie wall śpiący `fetch_image` miał większość próbek własnych
w tym oknie. Z kolei wada W2 (`_sepia_naive`) jest dobrze widoczna w obu
trybach. Tryb wall ma swoją cenę: **w profilu całego serwisu bezczynne
czekanie może przesłaniać koszty** (wątki puli w `Condition.wait`, pętla
zdarzeń w `select()`). Szukaj po nazwie funkcji albo traktuj tag `endpoint`
jako wskazówkę, nie miarę żądania (zob. granice tagów niżej), a latencję zmierz
osobno. Dokładne udziały zależą od maszyny, obciążenia i okna czasu — zmierz
je sam.

**Granice profilera (skrót; pełna lekcja w ćwiczeniu 11).**
- *Wall pokazuje blokujące wywołania na wątku, który je wykonuje.* `sleep`
  w `async def` stoi na wątku pętli, więc jest widoczny. Ale korutyna
  **zawieszona** na `await` nie jest na aktywnym stosie żadnego wątku, a
  używane tu profilery samplujące odczytują tylko takie stosy — czekanie na
  odpowiedź sieci przez `await` nie pojawia się jako ramki tej korutyny
  (co najwyżej zobaczysz pętlę zdarzeń w `select()`). Takie czekanie mierzysz
  czasem: latencją żądania (`curl -w '%{time_total}'`), pomiarem w aplikacji
  albo rozszerzeniem `trace` w httpx dla zdarzeń transportu.
- *Tagi wątkowe i `asyncio`.* `tag_wrapper` dołącza tag do bieżącego
  **wątku** na czas trwania bloku. Endpointy `def` działają w wątkach puli
  (współdzielonych w czasie, jedno żądanie naraz na wątek), więc tag oznacza
  próbki z tego wątku zebrane w czasie trwania otagowanego bloku — niekoniecznie
  cały koszt żądania. Handlery `async def` dzielą jeden wątek
  pętli, więc tagi współbieżnych żądań się nakładają: `endpoint=fetch` potrafi
  zawierać inną pracę na wątku pętli (np. importy, ramki innych żądań)
  i bezczynne czekanie w `select()`. Nie traktuj tagu endpointu `async def`
  jako dokładnego podziału na żądania.
- *`idle`.* Próbki bezczynnych wątków (czekanie na zadanie, na zegar) to nie
  „obciążenie" — w wall trzeba je odfiltrować, w cpu odrzuca je heurystyka
  bezczynności.

**Częsta pomyłka.** Wykluczenie wolnego endpointu jako wąskiego gardła,
bo w profilu CPU ma mało próbek. Najpierw sprawdź zakres i filtry. Ustawienie
kursowe `gil_only=True` może pominąć pracę natywną bez GIL. Porównaj czas
zegarowy i CPU w tym samym zakresie (`real` z `user + sys` w `time`).
W kontrolowanym przebiegu jednowątkowym duża różnica sugeruje czekanie lub
inny czas poza CPU. Czas CPU procesu sumuje się po wątkach i może przekroczyć
czas zegarowy. Do analizy blokujących wywołań przydaje się profil wall-clock,
a do oczekiwania w zawieszonych korutynach pomiar latencji żądań.

---

## Flamegraf — jak czytać

**Definicja.** Flamegraf to wizualizacja profilu stosu wywołań: każda pozioma
**ramka** (frame) to jedna funkcja. Oś **Y** (pionowa) to **głębokość stosu
wywołań** — im wyżej, tym głębiej w łańcuchu wywołań (funkcja u dołu wywołała
funkcję nad nią, ta wywołała kolejną, itd.). Oś **X** (pozioma) to **NIE
czas chronologiczny** — to agregacja próbek, zwykle posortowana alfabetycznie
albo według częstości, tak żeby te same ścieżki wywołań sąsiadowały ze sobą i
się sumowały w jedną szeroką ramkę. **Szerokość ramki** jest proporcjonalna
do liczby próbek, w których dana funkcja była na stosie — to jest właściwa
miara „ile czasu/próbek to kosztowało", z rozróżnieniem: **self time**
(czas/próbki spędzone BEZPOŚREDNIO w kodzie tej funkcji, nie licząc funkcji
przez nią wywoływanych) i **total time** (self time tej funkcji + total time
wszystkich funkcji wywołanych przez nią, czyli pełna szerokość ramki wraz
z częściami przykrytymi przez potomków). **Kolor** zwykle NIE ma znaczenia
semantycznego — to losowa paleta dla czytelności (odróżnienia sąsiadujących
ramek), choć niektóre narzędzia potrafią kolorować według modułu/pakietu;
znaczenie koloru zależy od narzędzia i widoku, więc sprawdź legendę.

**Intuicja.** To przekrój geologiczny. Im szersza warstwa, tym więcej próbek.
Szerokość nieprzykryta przez ramki potomne to udział własny — szeroka ramka,
nad którą nic nie ma, sama zjada dużo czasu (self time). Szeroka ramka przy
dole to zwykle tylko korzeń (`main`, serwer, wątek) z dużym total i małym self.
Wysoka, wąska „wieża” pokazuje głęboki łańcuch obecny w małej części próbek.

**Po co to.** Umiejętność odróżnienia self time od total time to podstawowa
umiejętność diagnostyczna tego kursu. Dla wady W2 (`_sepia_naive`) flamegraf
pod obciążeniem pokaże BARDZO SZEROKĄ ramkę bezpośrednio w tej funkcji (wysoki
self time — sama pętla `for y / for x` zjada czas, nie funkcje przez nią
wołane). Dla wady W3a (nowy klient HTTP przy każdym żądaniu, ćwiczenie 12)
w przebiegu opisanym w tym ćwiczeniu, w presecie cpu i po filtrze
`endpoint=fetch`, profil CPU pokazał tylko wąski ślad — konstruktor klienta
(`create_default_context`, `AsyncClient.__init__`) miał mały udział w próbkach.
To, czy prawdziwy koszt leży gdzie indziej (np. w otwieraniu nowych połączeń),
jest hipotezą do sprawdzenia innymi pomiarami — liczbą połączeń, latencją, CPU
na żądanie — a nie czymś, czego dowodzi wąska ramka. To dobra lekcja: szerokość
ramki to udział w *próbkach* z wybranego zakresu czasu, a nie w tym, co boli
w systemie. Rozróżnienie „gdzie faktycznie stoi problem" (self time) od „co
jest kosztowne jako całość" (total time) determinuje, CO naprawiasz.

**Częsta pomyłka.** „Ramka po lewej stronie flamegrafu wykonała się PRZED
ramką po prawej." Nie — oś X nie jest osią czasu (to nie jest to samo co
timeline/trace Gantta). Kolejność poziomo to efekt sortowania (zwykle
alfabetycznego dla ramek na tym samym poziomie), nie chronologii. Jeśli
potrzebujesz osi czasu (np. „co się działo w tej sekundzie"), użyj widoku
uporządkowanego w czasie (np. `py-spy record --format speedscope` albo
`chrometrace`) albo zawęź zakres czasu w Pyroscope przed czytaniem flamegrafu.
`py-spy dump` pokazuje pojedynczy zrzut wszystkich stosów w jednej chwili, nie
oś czasu.

---

## Continuous profiling vs profilowanie ad-hoc

**Definicja.** **Continuous profiling** (tu: Pyroscope) to profilowanie
działające stale na DZIAŁAJĄCEJ aplikacji (np. w produkcji albo pod loadgenem
przez cały czas jego trwania; w tej konfiguracji wykorzystuje próbkowanie
z niską częstotliwością), z profilami zbieranymi, tagowanymi (`tag_wrapper`,
ćwiczenie 04) i przechowywanymi w backendzie z możliwością porównywania
okresów w czasie (np. „profil przed wdrożeniem" vs „profil po wdrożeniu",
ćwiczenie 15). **Profilowanie ad-hoc** to ręczne uruchomienie narzędzia
(`py-spy record`, `cProfile`, `memray run`) na żądanie, dla konkretnego,
zwykle krótkiego przebiegu, żeby dostać jednorazowy, szczegółowy raport.

**Intuicja.** Continuous profiling to kamera monitoringu nagrywająca ciągle w
tle, ustawiona tak, by kosztowała niewiele — pozwala później „przewinąć"
i zobaczyć, co się działo o danej godzinie, albo porównać wczoraj z dziś.
Profilowanie ad-hoc to wyciągnięcie szczegółowego sprzętu pomiarowego na
chwilę, żeby zbadać jeden konkretny incydent tu i teraz.

**Po co to.** W tym kursie Pyroscope (ćwiczenia 1, 4, 15) daje Ci ciągły
wgląd w to, co dzieje się pod loadgenem, i mechanizm porównania profili w
czasie (regresja wydajności między wersjami, W8, ćwiczenie 15) — to jest
narzędzie „gdzie ogólnie szukać". Porównuj profile o tej samej miarze
i presecie, dla porównywalnego obciążenia i okien, z równoważnymi filtrami poza
badaną różnicą. Gdy badasz regresję wdrożenia, wersja aplikacji jest właśnie
badaną różnicą. `py-spy` (ćwiczenie 2), `cProfile`+`snakeviz` (ćwiczenie 3),
`tracemalloc` (ćwiczenie 7) i `memray` (ćwiczenia 8–9) to narzędzia ad-hoc —
gdy już wiesz z Pyroscope, że problem jest np. w module `images.py`, sięgasz
po nie, żeby dostać statystyki wywołań funkcji lub szczegóły alokacji,
zależnie od narzędzia.

**Częsta pomyłka.** „Skoro mam continuous profiling, nie potrzebuję nic
więcej." W tym kursie Pyroscope zbiera tylko próbki stosów CPU/wall-clock —
profilowanie pamięci w kliencie (`mem_enabled` w `pyroscope-io`) zostaje przy
wartości domyślnej, wyłączone — więc NIE pokazuje tu pamięci (alokacji,
wycieków) ani nie daje liczników zaobserwowanych wywołań takich jak
`cProfile`. Do pamięci używasz `tracemalloc`/`memray` (ad-hoc).

---

## Jak to się łączy (mapa)

```
CPython (standardowy build, z GIL) wykonuje bytecode w pętli interpretera
        │
        ├─ GIL: jeden wątek na raz wykonuje bytecode ──────── 09a, ćw. 10-11
        │
        ├─ pamięć: refcounting (natychmiast) + GC (nieosiągalne cykle) ── 06a, ćw. 7-9
        │        + pymalloc (areny/pule) → RSS a "zwolnione"
        │
        └─ narzut per-instrukcja → Python-pętla wolniejsza
           niż kod C (Pillow/numpy) ─────────────────────────  04a, ćw. 5-6

Jak na to patrzysz:
        sampling (py-spy, Pyroscope)  vs  tracing (cProfile)
                    │                           │
             estymacja z próbek         liczniki wywołań, czasy pod profilerem
                    │
        on-CPU (liczy)  vs  wall-clock (liczy + czas poza CPU) ── 11a, ćw. 11-14
                    │       (presety Pyroscope cpu/wall: filtry próbek wybierane
                    │        przy starcie, nie pomiar planisty;
                    │        granice: await, tagi w async)
                    │
              flamegraf: Y=głębokość, X=agregacja (NIE czas),
              pełna szerokość=total, część nieprzykryta przez potomków=self
                    │
        ad-hoc (py-spy/cProfile/tracemalloc/memray, ręcznie)
                    vs
        continuous (Pyroscope, ciągle, porównywalne w czasie) ── ćw. 1, 4, 15
```

Teraz przejdź do `01.md` (setup Pyroscope) — pierwsza czytanka blokowa,
`04a-cpu-od-srodka.md`, czeka przed ćwiczeniami 5-6.
