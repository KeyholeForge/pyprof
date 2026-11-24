# origin = nginx (HTTP/1.1, keep-alive) + an optional network delay (tc netem).
# The delay simulates a "distant" server: without it a response from localhost comes back in
# a fraction of a millisecond and parallel downloading (ex. 13) has nothing to shorten.
FROM nginx:1.30-alpine
RUN apk add --no-cache iproute2
COPY docker/origin-netem.sh /docker-entrypoint.d/05-netem.sh
RUN chmod +x /docker-entrypoint.d/05-netem.sh
