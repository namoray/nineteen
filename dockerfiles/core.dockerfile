FROM python:3.11-slim

WORKDIR /app



COPY requirements/core.txt /app/requirements.txt
COPY setup.py /app/setup.py
COPY README.md /app/README.md
RUN pip install --no-cache-dir -e . 

COPY . /app

CMD ["tail", "-f", "/dev/null"]