#!/usr/bin/env bash
# Run the full VoltEdge Load Management demo from the CLI with newman (Postman CLI).
# The collection is self-contained: the "Onboarding" folder registers the area + its
# 24 chargers and starts the baseline load — all via real API calls — so no seeding
# or external script is needed. Run it against an EMPTY database:
#   docker compose up
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

npx --yes newman run "$DIR/VoltEdge-LoadManagement.postman_collection.json" \
  --environment "$DIR/VoltEdge-Local.postman_environment.json" \
  --reporters cli
