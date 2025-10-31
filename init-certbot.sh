#!/bin/bash

set -euo pipefail

COMPOSE_FILE="docker-compose.server.yml"
DOMAIN="platform.smartview.top"
WEBROOT="/var/www/certbot"

echo ">> Stopping existing web service (if any)..."
docker compose -f "${COMPOSE_FILE}" rm -sf web || true

echo ">> Building temporary HTTP-only image..."
docker compose -f "${COMPOSE_FILE}" --profile certbot build web-http

echo ">> Starting temporary HTTP-only service..."
docker compose -f "${COMPOSE_FILE}" --profile certbot up -d web-http

echo ">> Requesting certificate for ${DOMAIN}..."
docker compose -f "${COMPOSE_FILE}" run --rm --entrypoint /bin/sh certbot \
  -c "certbot certonly --webroot -w ${WEBROOT} -d ${DOMAIN}"

echo ">> Stopping temporary HTTP-only service..."
docker compose -f "${COMPOSE_FILE}" --profile certbot rm -sf web-http

echo ">> Bringing up full stack..."
docker compose -f "${COMPOSE_FILE}" up -d --build --remove-orphans db backend web certbot

echo ">> Done. HTTPS should now be active for https://${DOMAIN}"
