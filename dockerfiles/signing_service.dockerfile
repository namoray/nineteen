FROM python:3.11-slim

WORKDIR /app/validator/signing_service
COPY validator/signing_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY validator/signing_service/src ./src
COPY validator/signing_service/pyproject.toml .


WORKDIR /app

ENV PYTHONPATH="${PYTHONPATH}:/app/validator/signing_service/src"

CMD ["python", "-u", "/app/validator/signing_service/src/main.py"]




