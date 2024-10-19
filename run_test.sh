docker compose --env-file .vali.env -f docker-compose.dev.yml -f docker-compose.contender-test.yml --profile entry_node_profile up -d --build
sleep 10
docker logs test_node