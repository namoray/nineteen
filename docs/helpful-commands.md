Helpful Docker Commands

## Docker

### Start services
```bash
docker-compose --env-file .prod.env -f docker-compose.prod.yml up -d
```

### View logs
```bash
docker-compose --env-file .prod.env -f docker-compose.prod.yml logs -f
```

### Stop services
```bash
docker-compose --env-file .prod.env -f docker-compose.prod.yml down
```

### Rebuild and start services
```bash
docker-compose --env-file .prod.env -f docker-compose.prod.yml up --build
```

### View running containers
```bash
docker ps
```