FROM python:3.14-slim

WORKDIR /app

RUN pip install poetry

COPY pyproject.toml ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# The agent code will be mounted at /workspace
WORKDIR /workspace

CMD ["python", "main.py"]
