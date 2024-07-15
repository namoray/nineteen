FROM python:3.9-slim

WORKDIR /app

COPY . /app

COPY requirements/core.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt


CMD ["tail", "-f", "/dev/null"]