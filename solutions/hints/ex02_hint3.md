# ex02 — hint 3: Pseudokod / gotowa komenda

```bash
PID=$(curl -s 127.0.0.1:8040/health | python -c "import sys, json; print(json.load(sys.stdin)['pid'])")
sudo py-spy top --pid $PID
sudo py-spy dump --pid $PID --locals > profiles/ex02_dump.txt
```
(Uruchom obie komendy py-spy, póki `loadgen.py --scenario filters` jeszcze
działa. Jeśli `sudo` nie znajduje `py-spy` ze środowiska wirtualnego, użyj
`sudo "$(command -v py-spy)" …`. Na Linuksie zwykle też potrzebne jest `sudo`;
możesz je pominąć tylko wtedy, gdy pozwalają na to polityka ptrace systemu i
Twoje uprawnienia (np. `kernel.yama.ptrace_scope` = 0 albo `CAP_SYS_PTRACE`).
Bez `sudo` w ogóle wykonaj całe ćwiczenie w jednym kontenerze Linux
uruchomionym z `--cap-add SYS_PTRACE -it` — z repozytorium i korpusem w
środku, dodatkowymi terminalami przez `docker exec` i PID odczytanym bez
`curl`, jeśli obraz go nie ma (patrz „Teoria w pigułce”). `py-spy top` wymaga
terminala TTY. `check.py ex02` to heurystyka treści: plik musi mieć wątki —
`Thread` — i ścieżki `app/`; linię `Process <pid>` w zrzucie porównaj z
`/health` samodzielnie.)
