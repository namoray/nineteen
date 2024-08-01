FROM core

WORKDIR /app/validator/control_center
COPY validator/control_center/pyproject.toml validator/control_center/requirements.txt ./
RUN pip install --no-cache-dir -e .

COPY validator /app/validator
WORKDIR /app

ENV PYTHONPATH=/app:$PYTHONPATH

CMD ["tail", "-f", "/dev/null"]