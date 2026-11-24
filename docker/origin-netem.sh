#!/bin/sh
# Dodaje stałe opóźnienie ORIGIN_DELAY_MS (ms) do pakietów wychodzących z kontenera.
# ORIGIN_DELAY_MS=0 wyłącza opóźnienie.
DELAY="${ORIGIN_DELAY_MS:-0}"
if [ "$DELAY" != "0" ]; then
  tc qdisc replace dev eth0 root netem delay "${DELAY}ms" \
    && echo "origin: opóźnienie sieciowe ${DELAY} ms (tc netem)" \
    || echo "origin: UWAGA, nie udało się ustawić tc netem (brak NET_ADMIN?) — bez opóźnienia"
fi
