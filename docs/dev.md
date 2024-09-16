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


## For dev without docker:
```bash
python -m venv .venv || python3 -m venv .venv
source .venv/bin/activate
find . -name "requirements.txt" -exec pip install -r {} \;
pip install --no-cache-dir git+https://github.com/namoray/fiber.git@dev
task dev_setup
task control_node_dev  # For example
```