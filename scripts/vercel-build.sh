#!/usr/bin/env sh
set -eu
python manage.py check
python manage.py collectstatic --noinput
# Never migrate a production database from unreviewed preview builds.
if [ "${VERCEL_ENV:-}" = "production" ]; then
  python manage.py migrate --noinput
fi
