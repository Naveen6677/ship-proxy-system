# client/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy client code
COPY ship_proxy.py /app/

# Copy entire proxy folder
COPY ../proxy /app/proxy

# Expose port for incoming requests
EXPOSE 8080

# Use environment variables for offshore host/port
ENV OFFSHORE_HOST=offshore
ENV OFFSHORE_PORT=9999

CMD ["python", "ship_proxy.py", "--offshore-host", "${OFFSHORE_HOST}", "--offshore-port", "${OFFSHORE_PORT}"]

