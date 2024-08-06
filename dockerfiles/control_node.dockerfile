FROM core

WORKDIR /app/validator/control_node

COPY validator/control_node/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY validator/control_node/src ./src
COPY validator/control_node/pyproject.toml .


ENV PYTHONPATH="${PYTHONPATH}:/app/validator/control_node/src"

CMD ["tail", "-f", "/dev/null"]