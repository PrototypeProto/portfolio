#!bin/sh

alembic upgrade head
fastapi dev src/__init__.py --host 0.0.0.0 --port 8000 --reload