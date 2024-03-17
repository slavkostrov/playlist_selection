#/bin/bash

set -e

echo "Start reloading external DB"

alembic downgrade base
alembic upgrade head
poetry run python app/db/init_db.py

echo "DB reloaded"
