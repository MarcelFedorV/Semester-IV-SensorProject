FROM alpine:3.18

RUN apk add --no-cache sqlite tini

WORKDIR /app/data

COPY users.db* /app/data/

RUN chmod 755 /app/data

VOLUME ["/app/data"]

ENTRYPOINT ["/sbin/tini", "--"]

CMD ["sh", "-c", "echo 'SQLite database container running. Database available at /app/data/users.db' && tail -f /dev/null"]
# The database is accessed via volume mounts by other containers