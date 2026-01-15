#!/usr/bin/env bash
set -euo pipefail

IMAGE_REPO="${IMAGE_REPO:-ghcr.io/diegogallegos4/agentbeats-challenge}"
GREEN_TAG_LATEST="${IMAGE_REPO}:latest"
GREEN_TAG="${IMAGE_REPO}:green"
PURPLE_TAG="${IMAGE_REPO}:purple"

echo "Building green image..."
docker build -f Dockerfile.green -t "${GREEN_TAG_LATEST}" -t "${GREEN_TAG}" .

echo "Building purple image..."
docker build -f Dockerfile.purple -t "${PURPLE_TAG}" .

echo "Done: ${GREEN_TAG_LATEST} ${GREEN_TAG} ${PURPLE_TAG}"
