#!/usr/bin/env bash
# build.sh

set -o errexit # Quitte immédiatement si une commande échoue

echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Applying database migrations..."
python manage.py migrate

echo "Build process completed."