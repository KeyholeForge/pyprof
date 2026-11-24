# ex02 — hint 2: Which API/tool

Find the PID: `curl -s 127.0.0.1:8040/health` (the `pid` field). Live view: `py-spy top --pid
<PID>`. Snapshot with local variables: `py-spy dump --pid <PID> --locals`.
Both commands attach to another process, so they need privileges: on macOS
always `sudo`, on Linux usually `sudo` too. Run them while loadgen is still
sending traffic.
