#!/bin/bash

set -a
source .vali.env
set +a

if [ -n "$ORGANIC_SERVER_PORT" ]; then
  echo "ORGANIC_SERVER_PORT is set to '$ORGANIC_SERVER_PORT'. Starting entry_node service."
  docker compose --env-file .vali.env -f docker-compose.yml --profile entry_node_profile up -d --build --remove-orphans
else
  echo "ORGANIC_SERVER_PORT is not set. Starting without entry_node service."
  docker compose --env-file .vali.env -f docker-compose.yml up -d --build --remove-orphans
fi