#!/usr/bin/env bash
# Build the YN baseline via the API, then run the Postman collection with newman.
# The system starts EMPTY, so we populate it first (exactly as a customer would,
# through real REST calls) before exercising the collection.
#
# Requires the stack to be running:  docker compose up
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"

echo "==> Bygger YN-baseline via API'et (populator)…"
docker compose -f "$ROOT/docker-compose.yml" exec -T backend python scripts/populate_demo.py

echo "==> Kører Postman-collectionen (newman)…"
npx --yes newman run "$DIR/VoltEdge-LoadManagement.postman_collection.json" \
  --environment "$DIR/VoltEdge-Local.postman_environment.json" \
  --reporters cli
