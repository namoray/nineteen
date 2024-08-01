FROM core

WORKDIR /app/validator/client_node

COPY validator/client_node/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY validator/client_node/src ./src
COPY validator/client_node/pyproject.toml .


ENV PYTHONPATH="${PYTHONPATH}:/app/validator/client_node/src"

CMD ["tail", "-f", "/dev/null"]