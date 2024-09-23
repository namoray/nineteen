# Instructions to help devs (Mainly Notes to self)

## Spin up all services for dev

Same as always
```bash
docker compose --env-file .vali.env -f docker-compose.yml  up -d
```
use run this
```bash
sed -i 's/ENV=[^ ]*/ENV=dev/' .vali.env
```

## Utils

** UTILS **
```bash
docker compose --env-file .vali.env -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```




## For dev without docker:

Optional if you need a venv
```bash
python -m venv .venv || python3 -m venv .venv
```

```bash
source .venv/bin/activate
find . -path "./venv" -prune -o -path "./.venv" -prune -o -name "requirements.txt" -exec pip install -r {} \;
pip install --no-cache-dir git+https://github.com/rayonlabs/fiber.git@0.0.2
task dev_setup
task control_node_dev  # For example
```


**If you want to dev with fiber locally too**
```bash
cd ..
git clone https://github.com/rayonlabs/fiber.git@0.0.2
cd fiber
git pull
pip install -e .
cd ..
cd nineteen
```

as you were