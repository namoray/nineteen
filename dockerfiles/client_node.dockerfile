FROM core

WORKDIR /app
COPY validator /app/validator
WORKDIR /app/validator/client_node
RUN pip install --no-cache-dir -e .


WORKDIR /app

ENV PYTHONPATH=/app:$PYTHONPATH

CMD ["tail", "-f", "/dev/null"]