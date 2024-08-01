FROM python:3.11-slim

WORKDIR /app/validator/signing_service
COPY validator/signing_service/pyproject.toml validator/signing_service/requirements.txt ./
RUN pip install --no-cache-dir -e .


COPY validator/signing_service /app/validator/signing_service
WORKDIR /app

# Set PYTHONPATH to include /app
ENV PYTHONPATH=/app:$PYTHONPATH

CMD ["python", "-u", "/app/validator/signing_service/main.py"]