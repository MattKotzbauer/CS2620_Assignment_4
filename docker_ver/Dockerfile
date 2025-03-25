# Use a lightweight Python base image
FROM python:3.9-slim

# Create and switch to a directory in the container
WORKDIR /app

# Copy requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire directory (raft_server.py, cluster_config.json, etc.)
COPY . /app

# We'll assume the default port is 50051, but we can override
EXPOSE 50051

# By default, just show help or something. We'll override CMD below.
CMD ["python", "raft_server.py", "--help"]

ENTRYPOINT ["python", "raft_server.py"]


