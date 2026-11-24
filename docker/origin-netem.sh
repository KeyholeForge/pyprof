#!/bin/sh
# Adds a constant delay of ORIGIN_DELAY_MS (ms) to packets leaving the container.
# ORIGIN_DELAY_MS=0 turns the delay off.
DELAY="${ORIGIN_DELAY_MS:-0}"
if [ "$DELAY" != "0" ]; then
  tc qdisc replace dev eth0 root netem delay "${DELAY}ms" \
    && echo "origin: network delay ${DELAY} ms (tc netem)" \
    || echo "origin: NOTE, failed to set tc netem (missing NET_ADMIN?) — no delay"
fi
