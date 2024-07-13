# Instructions to help devs (Mainly Notes to self)

## Spin up all services
```bash
docker-compose up -d
```

## Run Dev Panel

1. Spin up all services with the above ^
2. Run the following commands

```bash
. venv/bin/activate
pip install -r requirements.dev.txt
streamlit run tests/ui.py
```

Observe logs in the console for extra info