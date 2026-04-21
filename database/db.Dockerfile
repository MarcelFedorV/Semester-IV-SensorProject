# SQLite Database Container for users.db
FROM alpine:3.18

# Install SQLite3 and other utilities
RUN apk add --no-cache sqlite tini

# Create database directory
WORKDIR /app/data

# Copy existing database if present
COPY users.db* /app/data/

# Set permissions
RUN chmod 755 /app/data

# Create volume mount point
VOLUME ["/app/data"]

# Use tini as entrypoint to handle signals properly
ENTRYPOINT ["/sbin/tini", "--"]

# Keep container running - SQLite doesn't need a service daemon
# The database is accessed via volume mounts by other containers
CMD ["sh", "-c", "echo 'SQLite database container running. Database available at /app/data/users.db' && tail -f /dev/null"]