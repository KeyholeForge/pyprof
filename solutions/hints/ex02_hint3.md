# ex02 — hint 3: Pseudocode / ready-made command

```bash
PID=$(curl -s 127.0.0.1:8040/health | python -c "import sys, json; print(json.load(sys.stdin)['pid'])")
sudo py-spy top --pid $PID
sudo py-spy dump --pid $PID --locals > profiles/ex02_dump.txt
```
(Run both py-spy commands while `loadgen.py --scenario filters` is still
running. If `sudo` cannot find `py-spy` from your virtual environment, use
`sudo "$(command -v py-spy)" …`. On Linux `sudo` is usually needed as well;
you can skip it only if the system's ptrace policy and your permissions allow
it (e.g. `kernel.yama.ptrace_scope` = 0 or `CAP_SYS_PTRACE`). Without `sudo` at
all, run the whole exercise in one Linux container started with
`--cap-add SYS_PTRACE -it` — with the repository and corpus inside, the extra
terminals via `docker exec`, and the PID read without `curl` if the image has
none (see "Theory in a nutshell"). `py-spy top` requires
a TTY terminal. `check.py ex02` is a content heuristic: the file must contain
threads — `Thread` — and `app/` paths; compare `Process <pid>` in the dump
with `/health` yourself.)
