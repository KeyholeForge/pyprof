# 04a. Czytanka: CPU od środka

Czytanka, nie ćwiczenie — bez zadań i kryteriów „done". Cel: zbudować mapę
pojęć zanim wejdziesz w ćwiczenia 5-6 (blok B: CPU). Każde pojęcie w schemacie:

> **Definicja** → **Intuicja/analogia** → **Po co to** → **Częsta pomyłka**

Wracaj tu, gdy coś przestanie się spinać. Krótkie definicje powiązanych pojęć
(bytecode, pętla interpretera, GC, profilery) są w `slownik.md`.

---

## Koszt operacji w Pythonie: interpreter overhead per-instrukcja

**Definicja.** W uproszczeniu każda instrukcja bytecode w CPython (np.
`BINARY_OP` przy dodawaniu albo indeksowaniu listy, `LOAD_ATTR` przy dostępie
do atrybutu) przechodzi przez cykl pętli interpretera: pobranie instrukcji,
dekodowanie, dispatch do odpowiedniego kodu C, aktualizacja stosu wartości.
Ten narzut dispatchu płacisz przy każdej instrukcji, niezależnie od tego, jak
„prosta" logicznie jest operacja. Od 3.11 interpreter adaptacyjny
specjalizuje gorące instrukcje pod napotkane typy (a CPython 3.14 łączy też
niektóre pary instrukcji w jedną), co obniża narzut, ale go nie usuwa — a
praca za poszczególnymi instrukcjami jest różna, więc nie ma jednego kosztu
instrukcji. Do tego wartości w Pythonie są obiektami: dodanie dwóch liczb to
sprawdzenie typów i obiekt wyniku, nie sama arytmetyka. Dlatego dodanie dwóch
liczb w Pythonie kosztuje wielokrotnie więcej cykli procesora niż to samo
dodanie w skompilowanym kodzie C.

**Intuicja.** Licząc ręcznie na kalkulatorze musisz za każdym razem wcisnąć
kilka klawiszy (interpretacja), nawet dla trywialnego dodawania 2+2. Excel z
gotową formułą wektorową (analogia jednego wywołania kodu C, np. Pillow/numpy)
liczy tysiąc takich dodawań w jednym poleceniu, bez powtarzania narzutu
„wciskania klawiszy" tysiąc razy.

**Po co to.** To wprost tłumaczy, dlaczego pętla w czystym Pythonie nad
milionami elementów jest dużo wolniejsza niż wektoryzowana operacja w
bibliotece C („wektoryzowana" znaczy tu: pętla wykonuje się wewnątrz jednego
wywołania skompilowanego kodu). Weź `app/images.py::_sepia_naive` — dla dużego
obrazu z korpusu (2000×1500 = 3 000 000 pikseli) funkcja robi PODWÓJNĄ pętlę
Pythona, z kilkudziesięcioma instrukcjami bytecode na piksel (arytmetyka,
wywołania `int` i `min`, odczyt i zapis piksela). To 3 mln przebiegów
wewnętrznej pętli Pythona, a w każdym narzut interpretera płacony wiele razy,
przy każdej instrukcji. Naprawiona wersja,
`img.convert("RGB", matrix=SEPIA_MATRIX)`, stosuje tę samą matematykę (te same
współczynniki 3×3 na piksel; kanały wyniku mogą różnić się o jeden poziom, bo
Pillow zaokrągla, a `_sepia_naive` obcina przez `int()`), ale CAŁA pętla po
pikselach wykonuje się wewnątrz jednego wywołania C w Pillow — interpreter
Pythona wykonuje jedno wywołanie metody, ze stałą liczbą kroków niezależnie od
liczby pikseli, zamiast 3 milionów przebiegów pętli. Duża różnica w czasie
wykonania nie bierze się z „lepszego algorytmu" (obie wersje odwiedzają każdy
piksel raz) — bierze się z tego, GDZIE fizycznie wykonuje się pętla: w
interpreterze Pythona, z całą pythonową pracą na każdy piksel, czy w
skompilowanym kodzie C. Porównanie czasu obu wersji mierzy całą tę różnicę,
nie sam narzut dispatchu.

**Częsta pomyłka.** „Skoro C jest szybszy, to każdą pętlę Pythona trzeba
przepisać ręcznie na C/Cython." Zwykle nie trzeba pisać własnego C — biblioteki
jak Pillow, numpy, pandas już dają zwektoryzowane operacje na typowych
strukturach danych (obrazy, tablice, ramki danych). Pierwszy krok to zawsze
sprawdzenie, czy istniejąca biblioteka ma gotową operację wysokopoziomową
(jak `Image.convert` z macierzą) zamiast pisania pętli od zera — dopiero gdy
takiej operacji nie ma, rozważa się Cython/numba/rozszerzenia C.

---

## Złożoność obliczeniowa a profil

**Definicja.** Złożoność obliczeniowa (notacja Big-O) opisuje, jak ilość
pracy rośnie wraz z rozmiarem danych wejściowych (ograniczenie z góry, przy
ustalonej mierze rozmiaru wejścia i pracy) — niezależnie od tego, w jakim
języku algorytm jest zaimplementowany. Profil (flamegraf, `cProfile`)
pokazuje FAKTYCZNY czas/liczbę próbek dla KONKRETNEGO uruchomienia z
KONKRETNYM rozmiarem danych — to punktowy pomiar, nie analiza asymptotyczna.

**Intuicja.** Złożoność to przepis („jeśli każdy wita się z każdym, N gości
potrzebuje około N²/2 uścisków dłoni — praca rośnie jak N²") — mówi jak rośnie
praca w teorii. Profil to stoper zmierzony na konkretnej imprezie z konkretną
liczbą gości — mówi ile faktycznie zajęło to TERAZ, na TYM sprzęcie, z TYMI
danymi.

**Po co to.** Profil sam z siebie nie powie Ci „to jest O(n²)" — pokazuje tylko,
że dana funkcja jest wolna DLA TEGO konkretnego wejścia. Żeby rozróżnić „wolne
bo dużo danych i to normalne" od „wolne bo zła złożoność", trzeba porównać czas
samej funkcji (nie całego żądania, które ma też koszty stałe) dla kilku
rozmiarów wejścia (np. `_sepia_naive` na małym obrazie z korpusu vs na dużym) i
zobaczyć, czy czas rośnie mniej więcej proporcjonalnie do liczby pikseli (co
jest oczekiwane — filtr musi dotknąć każdy piksel przynajmniej raz), czy
wyraźnie szybciej. Szybszy wzrost to powód, żeby sprawdzić kod (np. czy nie ma
przypadkowego zagnieżdżenia pętli O(n²) tam, gdzie wystarczy O(n)) i warunki
pomiaru; same czasy nie dowodzą klasy złożoności — dowodzi jej lektura kodu. W
tym kursie `_sepia_naive` jest liniowa (O(szerokość×wysokość)): jedno przejście
po pikselach ze stałą pracą na piksel — problem nie jest w złożoności, tylko w
tym, GDZIE fizycznie wykonuje się ta liniowa pętla (patrz wyżej). Inny przykład
z tego kursu: konkatenacja stringów w pętli (`report += line`, ćwiczenie 9, ★
Bonus B). `str` jest niemutowalny, więc jeśli każde dopisanie kopiuje cały
dotychczasowy tekst, a dopisywane fragmenty mają podobną długość, liczba
kopiowanych znaków rośnie kwadratowo względem liczby fragmentów — O(n²)
kopiowania. CPython 3.14 ma optymalizację (nie jest to gwarancja języka): może
czasem powiększyć bufor lokalnej zmiennej `str`, gdy wynik `s += x` trafia od
razu z powrotem do tej samej zmiennej. Brak innej referencji do stringa pomaga,
ale znaczenie ma też reprezentacja napisu i inne warunki, a powiększenie może
przenieść bufor. Optymalizacja nie działa m.in. dla zmiennej globalnej, atrybutu
(`self.report += line`) ani `bytes`. Czy dana pętla naprawdę płaci koszt
kwadratowy, zależy więc od kodu i interpretera — sprawdź to, zamiast zakładać
(ćw. 9 ★). Czy taki koszt ma znaczenie w serwisie, to osobne pytanie — odpowiada
na nie profil rzeczywistego obciążenia, nie izolowane porównanie. Lekcja:
złożoność mówi, jak koszt *rośnie*; profil mówi, czy to w ogóle jest *ten* koszt
— oba trzeba sprawdzić, zanim zaczniesz optymalizować.

**Częsta pomyłka.** „Ta funkcja ma dużo próbek w profilu, więc ma złą
złożoność algorytmiczną." Niekoniecznie — funkcja może mieć optymalną
złożoność (liniową, tak jak musi być, bo dotyka każdego piksela raz) i mimo
to być wolna, bo jest zaimplementowana w czystym Pythonie zamiast w
zwektoryzowanym kodzie C. „Dużo próbek" mówi CO jest kosztowne, nie DLACZEGO —
to wymaga dodatkowego rozumowania (czy to liniowa pętla w złym miejscu, czy
faktycznie O(n²)/O(n³)).

---

## Pułapki mikrobenchmarków

**Definicja.** Mikrobenchmark to pomiar czasu wykonania małego fragmentu kodu,
zwykle powtarzany wielokrotnie, żeby ocenić „czy wersja A jest szybsza od wersji
B". JavaScript w przeglądarce działa na silnikach JIT, które rozgrzewają się z
czasem. CPython 3.14 może zawierać eksperymentalny kompilator JIT; to, czy jest
dostępny i domyślnie włączony, zależy od buildu. Nawet bez aktywnego JIT
pierwsze uruchomienia danego kodu bywają wolniejsze niż kolejne, z kilku
powodów: jednorazowa praca (importy, pierwsze alokacje, specjalizacja instrukcji
przez interpreter adaptacyjny po kilku pierwszych wykonaniach), **cache
procesora** (dane i instrukcje trzeba pierwszy raz sprowadzić z wolniejszej
pamięci RAM do szybkiego cache L1/L2/L3) i **dysk/system plików** (pierwszy
odczyt pliku obrazu z korpusu może uderzać w fizyczny dysk, kolejne trafiają w
cache stron systemu operacyjnego — dużo szybciej). Do tego dochodzi **szum
systemowy**: inne procesy na maszynie, harmonogramowanie wątków przez OS. A w
Pythonie konkretnie **Garbage Collector może odpalić się W TRAKCIE pomiaru**:
gdy automatyczny cykliczny GC jest włączony, wystarczająco duża nadwyżka
alokacji nad dealokacjami obiektów obsługiwanych przez GC (kontenerów) od
ostatniego przebiegu może zaplanować zbiórkę, a jeśli kolektor wykona ją w
mierzonym przedziale, jego praca wliczy się do zmierzonego czasu. Tę pracę
wyzwalają alokacje — często samego mierzonego kodu — więc to nie czysty szum:
może być częścią rzeczywistego kosztu kodu. `timeit` domyślnie wyłącza
automatyczny cykliczny GC, żeby czasy były porównywalne, co ukrywa też ten
koszt; jeśli należy on do tego, co chcesz zmierzyć, włącz go jawnie i zapisz ten
wybór.

**Intuicja.** Mierzenie czasu przebiegnięcia trasy przez pojedynczego biegacza
jednego dnia nic nie mówi o jego przeciętnym czasie — musisz zmierzyć kilka
przebiegnięć (uwzględniając, że pierwszy start może być wolniej przez
rozgrzewkę) i patrzeć na najlepszy/typowy wynik, nie na pojedynczy — i pytać,
dlaczego wolny przebieg był wolny: mógł się zatrzymać, żeby zawiązać sznurówkę,
którą poluzował mu własny bieg (GC — wyzwalany przez pracę samego programu, więc
część jego rzeczywistego kosztu), albo akurat wiał przeciwny wiatr (inny proces
zajął CPU).

**Po co to.** W tym kursie dotyczy to bezpośrednio ćwiczeń CPU (5-6): kiedy
porównujesz `_sepia_naive` z wersją naprawioną (`img.convert` z macierzą),
pojedynczy pomiar czasu jednego requestu może wprowadzić w błąd. Praktyka:
(1) rób **wiele porównywalnych powtórzeń** (loadgen w tym kursie odpala wiele
requestów pod rząd, nie jeden; `timeit` powtarza fragment), (2) dobierz
statystykę do pytania i zachowaj wszystkie czasy: **minimum** (`timeit` podaje
najlepszy czas na pętlę) to mało zaszumione oszacowanie dla izolowanego
fragmentu — nie dowód, że nic nie przeszkadzało; **mediana** pokazuje
„typowy" czas odporny na pojedyncze anomalie; **średnia** jest wrażliwa na
pojedyncze odstające, wolne pomiary (np. jeden request trafiający na przebieg
GC); jeśli liczą się wolne requesty, patrz też na percentyl ogona, (3) zdecyduj,
czy pytasz o zachowanie na zimno, czy po rozgrzaniu, i mierz ten stan
konsekwentnie (po rozgrzaniu: odrzuć pierwsze przebiegi, które mogą jeszcze
czytać plik z dysku albo rozgrzewać cache).

**Częsta pomyłka.** „Zmierzyłem raz każdą wersję i A jest szybsza, więc A
wygrywa." Jeden pomiar to szum + sygnał zmieszane razem — bez powtórzeń nie
wiesz, czy różnica jest realna czy przypadkowa (np. GC odpalił się akurat
przy pomiarze B). Profilowanie pod loadgenem (jak w tym kursie) daje
setki/tysiące próbek stosu zamiast jednego pomiaru — lepiej pokazują, gdzie
poszedł czas w tym przebiegu, ale nie zastępują powtarzanych porównań przed i
po. Przy ręcznych porównaniach (np. `time` na pojedynczym curl) pamiętaj o
wielu powtórzeniach.

---

## Jak to się łączy (mapa)

```
Interpreter overhead per-instrukcja (00-teoria)
        │
        ├─ pętla Python (_sepia_naive) ── wolna nie przez złą złożoność,
        │                                  tylko przez GDZIE się wykonuje
        │
        ├─ zwektoryzowana operacja C (Pillow) ── ta sama matematyka
        │                                          (zaokrąglenie może różnić
        │                                          się o poziom), pętla
        │                                          wewnątrz jednego wywołania
        │
        └─ złożoność (Big-O) ── osobny wymiar: liniowa pętla w złym miejscu
                                 (sepia) vs kwadratowe kopiowanie, jeśli
                                 każde dopisanie kopiuje cały rosnący tekst
                                 (`+=` na stringach; CPython często potrafi
                                 tego uniknąć — sprawdź, ćw. 9 ★)

Pomiar tego:
        wiele porównywalnych powtórzeń → min (izolowany fragment) / mediana
        (typowy request), zachowaj wszystkie czasy; średnią ciągną odstające
        uwaga na: rozgrzewkę (cache CPU/dysku, specjalizacja), GC w trakcie
        pomiaru (w timeit domyślnie wyłączony), szum OS
```

Teraz przejdź do `05.md` (ćwiczenie: profilowanie i naprawa `_sepia_naive`).

---
