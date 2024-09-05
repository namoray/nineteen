# Instructions to help devs (Mainly Notes to self)

## Spin up all services for dev
```bash
docker-compose --env-file .dev.env -f docker-compose.dev.yml  up -d
```

## Utils

** UTILS FOR DEV **
```bash
docker-compose --env-file .dev.env -f docker-compose.dev.yml -f docker-compose.utils.yml up -d
```

** UTILS FOR PROD **
```bash
docker-compose --env-file .prod.env -f docker-compose.prod.yml -f docker-compose.utils.yml up -d
```