# ex03 — hint 2: Which API/tool

`cProfile.Profile()` + `.enable()`/`.disable()` around the function call,
`profiler.dump_stats(path)` saves the `.prof` file. `snakeviz <file.prof>`
starts a local server and tries to open a browser with an interactive chart
(`snakeviz -s <file.prof>` starts the server and prints the address without
opening a browser).
