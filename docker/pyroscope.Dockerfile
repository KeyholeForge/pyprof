# Obraz grafana/pyroscope:2.4.2 jest typu distroless (brak shella, curl, wget) —
# healthcheck compose wymaga realnego binarnego klienta HTTP wewnątrz
# kontenera. Ten Dockerfile dokleja statyczny binarny pyroscope (Go, bez
# zależności libc) na alpine z curl, wyłącznie po to, by healthcheck mógł
# wykonać `curl -f http://localhost:4040/ready` (patrz lekcja: healthcheck
# musi być realnym curl, nie statusem kontenera).
FROM grafana/pyroscope:2.4.2 AS pyroscope

FROM alpine:3.24
RUN apk add --no-cache curl
COPY --from=pyroscope /usr/bin/pyroscope /usr/bin/pyroscope
COPY --from=pyroscope /etc/pyroscope /etc/pyroscope
ENTRYPOINT ["/usr/bin/pyroscope"]
CMD ["-config.file=/etc/pyroscope/config.yaml"]
