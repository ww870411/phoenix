#!/bin/bash

set -euo pipefail

# Configuration
REGISTRY="${REGISTRY:-}"
BACKEND_IMAGE_NAME="${BACKEND_IMAGE_NAME:-phoenix-backend}"
FRONTEND_IMAGE_NAME="${FRONTEND_IMAGE_NAME:-phoenix-web}"
BACKEND_TAG="${BACKEND_TAG:-latest}"
FRONTEND_TAG="${FRONTEND_TAG:-latest}"

timestamp="$(date +%Y%m%d%H%M%S)"

backend_ref="${BACKEND_IMAGE_NAME}:${BACKEND_TAG}"
frontend_ref="${FRONTEND_IMAGE_NAME}:${FRONTEND_TAG}"

if [[ -n "${REGISTRY}" ]]; then
  backend_ref="${REGISTRY}/${backend_ref}"
  frontend_ref="${REGISTRY}/${frontend_ref}"
fi

echo ">> Building backend image (${backend_ref})"
docker build \
  -f backend/Dockerfile.prod \
  -t "${backend_ref}" \
  --build-arg BUILD_TIMESTAMP="${timestamp}" \
  .

echo ">> Building frontend image (${frontend_ref})"
docker build \
  -f deploy/Dockerfile.web \
  -t "${frontend_ref}" \
  --build-arg BUILD_TIMESTAMP="${timestamp}" \
  .

echo
echo "Build completed."
echo "Backend image: ${backend_ref}"
echo "Frontend image: ${frontend_ref}"
echo
if [[ -n "${REGISTRY}" ]]; then
  echo "You can push them with:"
  echo "  docker push ${backend_ref}"
  echo "  docker push ${frontend_ref}"
else
  echo "If you need to push to a registry, set REGISTRY, BACKEND_IMAGE_NAME, FRONTEND_IMAGE_NAME, BACKEND_TAG, FRONTEND_TAG environment variables."
fi
