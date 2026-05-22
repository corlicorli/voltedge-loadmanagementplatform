#!/usr/bin/env bash
# Run the full VoltEdge Load Management demo from the CLI with newman (Postman CLI).
# Requires Node.js. Start the stack first: docker compose up
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

npx --yes newman run "$DIR/VoltEdge-LoadManagement.postman_collection.json" \
  --environment "$DIR/VoltEdge-Local.postman_environment.json" \
  --reporters cli
