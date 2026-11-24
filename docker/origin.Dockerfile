# origin = nginx (HTTP/1.1, keep-alive) + opcjonalne opóźnienie sieciowe (tc netem).
# Opóźnienie symuluje „daleki” serwer: bez niego odpowiedź z localhosta wraca w
# ułamku milisekundy i równoległe pobieranie (ćw. 13) nie ma czego skrócić.
FROM nginx:1.30-alpine
RUN apk add --no-cache iproute2
COPY docker/origin-netem.sh /docker-entrypoint.d/05-netem.sh
RUN chmod +x /docker-entrypoint.d/05-netem.sh
