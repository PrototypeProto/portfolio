#!/bin/sh

alembic upgrade head
# exec uvicorn src:app --host 0.0.0.0 --port 8000 --reload --workers 4 # for prod
exec uvicorn src:app --host 0.0.0.0 --port 8000 --reload