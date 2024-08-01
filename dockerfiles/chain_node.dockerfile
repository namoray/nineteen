FROM core

WORKDIR /app/validator/chain_node

COPY validator/chain_node/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY validator/chain_node/src ./src
COPY validator/chain_node/pyproject.toml .


ENV PYTHONPATH="${PYTHONPATH}:/app/validator/chain_node/src"

CMD ["tail", "-f", "/dev/null"]