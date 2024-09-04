FROM core

WORKDIR /app/validator/entry_node

COPY validator/entry_node/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY validator/utils /app/validator/utils
COPY validator/models.py /app/validator/models.py
COPY validator/db /app/validator/db

COPY validator/entry_node/src ./src
COPY validator/entry_node/pyproject.toml .


ENV PYTHONPATH="${PYTHONPATH}:/app/validator/entry_node/src"

# CMD ["tail", "-f", "/dev/null"]