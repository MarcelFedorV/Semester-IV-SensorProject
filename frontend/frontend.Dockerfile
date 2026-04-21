# Frontend - Nginx Static File Server
FROM nginx:1.25-alpine

# Set metadata
LABEL maintainer="SensorProject"
LABEL description="Frontend static file server for the Sensor Project"

# Copy all HTML files
COPY pages/ /usr/share/nginx/html/

# Set proper permissions
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

# Start nginx in foreground
CMD ["nginx", "-g", "daemon off;"]