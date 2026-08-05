#!/bin/bash
set -e

echo "Pushing Prisma schema to database..."
prisma db push --accept-data-loss

echo "Seeding assembly lines..."
python prisma/seed.py

echo "Starting FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
