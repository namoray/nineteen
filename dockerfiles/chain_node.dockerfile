FROM core

WORKDIR /app

COPY validator /app/validator
WORKDIR /app/validator/chain_node
RUN pip install --no-cache-dir -e .

WORKDIR /app

ENV PYTHONPATH=/app:$PYTHONPATH


CMD ["python", "-u", "/app/validator/chain_node/main.py"]
