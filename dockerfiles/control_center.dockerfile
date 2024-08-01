FROM core

WORKDIR /app/validator/control_center

COPY validator/control_center/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY validator/control_center/src ./src
COPY validator/control_center/pyproject.toml .


ENV PYTHONPATH="${PYTHONPATH}:/app/validator/control_center/src"

CMD ["tail", "-f", "/dev/null"]