FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y gcc libffi-dev make\
    && pip install --no-cache-dir poetry \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Копируем зависимости
COPY pyproject.toml poetry.lock ./

# Устанавливаем зависимости
RUN poetry install --without dev --no-interaction --no-ansi --no-root

# Копируем только то, что нужно для работы
COPY src/bot ./bot/

CMD ["python", "-m", "bot.main"]