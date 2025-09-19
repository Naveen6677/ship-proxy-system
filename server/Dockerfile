# server/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy server code
COPY server.py /app/

# Copy entire proxy folder
COPY ../proxy /app/proxy

# Expose port for incoming TCP connection
EXPOSE 9999

CMD ["python", "server.py"]
