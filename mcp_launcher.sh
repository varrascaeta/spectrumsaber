#!/bin/bash
set -a
source "$(dirname "$0")/.env"
set +a

export GRAPHQL_HEADERS="{\"Content-Type\": \"application/json\", \"Authorization\": \"JWT ${GRAPHQL_JWT_TOKEN}\"}"

exec uv \
  --directory "$(dirname "$0")" \
  run text-to-graphql-mcp