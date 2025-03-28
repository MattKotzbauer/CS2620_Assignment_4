# build_and_run.ps1

# Stop any running containers.
docker-compose down

# Remove persistent data and logs.
Remove-Item -Recurse -Force data/
Remove-Item -Force client.log

# Build the Docker image.
docker build -t raft_server:latest .

# Run the demo.
python.exe .\demo.py
