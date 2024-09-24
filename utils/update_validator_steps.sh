#!/bin/bash

# THIS FILE CONTAINS THE STEPS NEEDED TO MANUALLY UPDATE THE REPO ON A TAG CHANGE
# THIS FILE ITSELF MAY CHANGE FROM UPDATE TO UPDATE, SO WE CAN DYNAMICALLY FIX ANY ISSUES

docker compose --env-file .vali.env -f docker-compose.yml  build
docker compose --env-file .vali.env -f docker-compose.yml run -e LOCALHOST=false --entrypoint "python /validator/utils/contender/nuke_contender_history.py" control_node
./utils/launch_validator.sh
echo "Update steps complete :)"
