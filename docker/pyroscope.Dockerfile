# The grafana/pyroscope:2.4.2 image is distroless (no shell, curl, wget) —
# the compose health check needs a real HTTP client binary inside
# the container. This Dockerfile adds the static pyroscope binary (Go, no
# libc dependency) onto alpine with curl, solely so that the health check can
# run `curl -f http://localhost:4040/ready` (the health check
# must be a real curl, not the container status).
FROM grafana/pyroscope:2.4.2 AS pyroscope

FROM alpine:3.24
RUN apk add --no-cache curl
COPY --from=pyroscope /usr/bin/pyroscope /usr/bin/pyroscope
COPY --from=pyroscope /etc/pyroscope /etc/pyroscope
ENTRYPOINT ["/usr/bin/pyroscope"]
CMD ["-config.file=/etc/pyroscope/config.yaml"]
