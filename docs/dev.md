# Instructions to help devs (Mainly Notes to self)

## Spin up all services for dev

Same as always
```bash
docker-compose --env-file .vali.env -f docker-compose.yml  up -d
```
use run this
```bash
sed -i 's/ENV=[^ ]*/ENV=dev/' .vali.env
```

## Utils

** UTILS FOR DEV **
```bash
docker-compose --env-file .vali.env -f docker-compose.yml -f docker-compose.utils.yml up -d
```

** UTILS FOR PROD **
```bash
docker-compose --env-file .vali.env -f docker-compose.yml -f docker-compose.utils.yml up -d
```


## For dev without docker:
```bash
python -m venv .venv || python3 -m venv .venv
source .venv/bin/activate
find . -name "requirements.txt" -exec pip install -r {} \;
pip install --no-cache-dir git+https://github.com/rayonlabs/fiber.git@dev
task dev_setup
task control_node_dev  # For example
```


**If you want to dev with fiber locally too**
```bash
cd ..
git clone https://github.com/rayonlabs/fiber.git
cd fiber
git pull
pip install -e .
cd ..
cd nineteen
```

as you were