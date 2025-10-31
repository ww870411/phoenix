#!/bin/bash

set -euo pipefail

COMPOSE_FILE="docker-compose.server.yml"
DOMAIN="platform.smartview.top"
WEBROOT="/var/www/certbot"

echo ">> Running certbot for ${DOMAIN} ..."
docker compose -f "${COMPOSE_FILE}" run --rm --entrypoint /bin/sh certbot \
  -c "certbot certonly --webroot -w ${WEBROOT} -d ${DOMAIN}"

echo ">> Certbot finished. Restarting web stack ..."
docker compose -f "${COMPOSE_FILE}" up -d --build --remove-orphans

echo ">> Done. Nginx should now serve HTTPS for ${DOMAIN}."
