#!/bin/bash

set -euo pipefail

REGISTRY="${REGISTRY:-}"
IMAGE_NAME="${IMAGE_NAME:-phoenix-all}"
TAG="${TAG:-latest}"

timestamp="$(date +%Y%m%d%H%M%S)"
image_ref="${IMAGE_NAME}:${TAG}"

if [[ -n "${REGISTRY}" ]]; then
  image_ref="${REGISTRY}/${image_ref}"
fi

echo ">> Building combined image (${image_ref})"
docker build \
  -f Dockerfile.full \
  -t "${image_ref}" \
  --build-arg BUILD_TIMESTAMP="${timestamp}" \
  .

echo
echo "Image built: ${image_ref}"
if [[ -n "${REGISTRY}" ]]; then
  echo "Push with: docker push ${image_ref}"
fi
