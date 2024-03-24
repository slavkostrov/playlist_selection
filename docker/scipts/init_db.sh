#/bin/bash

set -e

echo "Start init external DB"

alembic upgrade head
poetry run python app/db/init_db.py

echo "DB reloaded"
