#!/bin/bash
set -euo pipefail

# Start docker daemon for image build/push
(dockerd > /var/log/dockerd.log 2>&1 &)

# Give dockerd a moment to start
sleep 5

# Run snapshot job
poetry run python main.py
