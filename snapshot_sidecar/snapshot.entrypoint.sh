#!/bin/bash

# Start Docker daemon in the background
dockerd &

# Wait for Docker to be ready
echo "Waiting for Docker daemon..."
while ! docker info > /dev/null 2>&1; do
    sleep 1
done
echo "Docker is ready."

# Keep the container running
tail -f /dev/null
