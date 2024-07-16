FROM python:3.11-slim

WORKDIR /app



COPY requirements/core.txt /app/requirements.txt
COPY setup.py /app/setup.py
COPY README.md /app/README.md
RUN pip install --no-cache-dir -e . 

COPY core /app/core
COPY validator /app/validator

# Review below as it needs bittensor in places
COPY models /app/models

# Review below as don't want config plauging us
COPY config /app/config



CMD ["tail", "-f", "/dev/null"]