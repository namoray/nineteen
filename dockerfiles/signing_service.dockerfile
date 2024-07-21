FROM python:3.11-slim

WORKDIR /app


# Install signing_service service
COPY validator/signing_service /app/validator/signing_service
WORKDIR /app/validator/signing_service
RUN pip install --no-cache-dir -e .

# Set the working directory back to /app
WORKDIR /app

# Set PYTHONPATH to include /app
ENV PYTHONPATH=/app:$PYTHONPATH

