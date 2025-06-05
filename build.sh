#!/usr/bin/env bash
# Build script for DigitalOcean App Platform

set -o errexit  # exit on error

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate