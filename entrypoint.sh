#!/bin/bash
set -e

# wait for DB if needed (very simple)
if [ "$DATABASE_URL" != "" ]; then
  # optionally add wait-for logic here or rely on docker-compose restart policy
  :
fi

# collect static files
python manage.py collectstatic --noinput

# run migrations
python manage.py migrate --noinput

# run whatever command was sent
exec "$@"
