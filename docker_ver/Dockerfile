# Use a lightweight Python base image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV GRPC_DNS_RESOLVER=native
ENV GRPC_VERBOSITY=DEBUG

# Create and switch to a directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create data directory with proper permissions
RUN mkdir -p /app/data && chmod 777 /app/data

# Copy the entire directory (raft_server.py, cluster_config.json, etc.)
COPY . /app

# Ensure proper permissions for data directory
RUN chmod -R 777 /app/data

# We'll assume the default port is 50051, but we can override
EXPOSE 50051

# By default, just show help or something. We'll override CMD below.
CMD ["python", "raft_server.py", "--help"]

ENTRYPOINT ["python", "raft_server.py"]

