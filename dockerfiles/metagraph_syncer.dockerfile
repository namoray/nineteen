FROM python:3.11-slim

WORKDIR /app



# Install core package
COPY core /app/core
WORKDIR /app/core
RUN pip install --no-cache-dir -e .

# Install query_node service
COPY validator /app/validator
WORKDIR /app/validator/metagraph_syncer
RUN pip install --no-cache-dir -e .

# Copy models and config
COPY models /app/models
COPY config /app/config

# Set the working directory back to /app
WORKDIR /app

# Set PYTHONPATH to include /app
ENV PYTHONPATH=/app:$PYTHONPATH

CMD ["python3.11", "/app/validator/metagraph_syncer/metagraph_syncer.py"]