# ex02 — hint 2: Które API/narzędzie

Znajdź PID: `curl -s 127.0.0.1:8040/health` (pole `pid`). Live widok: `py-spy top --pid
<PID>`. Snapshot z lokalnymi zmiennymi: `py-spy dump --pid <PID> --locals`.
Obie komendy podłączają się do innego procesu, więc wymagają uprawnień: na
macOS zawsze `sudo`, na Linuksie zwykle też `sudo`. Uruchamiaj je, póki
loadgen jeszcze generuje ruch.
