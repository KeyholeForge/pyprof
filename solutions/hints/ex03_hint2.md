# ex03 — hint 2: Które API/narzędzie

`cProfile.Profile()` + `.enable()`/`.disable()` wokół wywołania funkcji,
`profiler.dump_stats(path)` zapisuje `.prof`. `snakeviz <plik.prof>`
uruchamia lokalny serwer i próbuje otworzyć przeglądarkę z interaktywnym
wykresem (`snakeviz -s <plik.prof>` uruchamia serwer i wypisuje adres bez
otwierania przeglądarki).
