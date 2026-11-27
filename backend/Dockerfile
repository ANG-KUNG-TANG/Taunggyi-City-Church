# Python runtime for the Django backend
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System dependencies required by mysqlclient and Python packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        pkg-config \
        default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# Install the project's pinned Python dependencies
COPY requirements/requirements.txt ./requirements/requirements.txt

RUN python -m pip install --no-cache-dir \
    -r requirements/requirements.txt

# Copy the backend source code
COPY . .

# Ensure runtime directories exist
RUN mkdir -p logs staticfiles media

EXPOSE 8000

# Start Django through its ASGI application.
# Migrations and collectstatic are intentionally not automatic.
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
