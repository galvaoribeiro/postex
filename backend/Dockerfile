FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-dev.txt ./
RUN pip install --upgrade pip && pip install -r requirements-dev.txt

COPY . .

EXPOSE 8000

# O entrypoint e um script Python (e nao shell) para nao depender de
# line endings LF, que se perdem facilmente em checkouts no Windows.
ENTRYPOINT ["python", "/app/docker-entrypoint.py"]
CMD ["api"]
