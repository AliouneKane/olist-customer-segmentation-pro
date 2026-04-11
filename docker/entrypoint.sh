#!/bin/sh
# Gunicorn startup for the Dash dashboard.
#
# Workers: 1 + threads 4 is the recommended pattern for Dash on Cloud Run.
# Multiple workers each load their own copy of the parquet files into RAM;
# Cloud Run scales by spinning new instances, not more workers per instance.
#
# PORT is injected by Cloud Run at container startup; defaults to 8080.
exec gunicorn \
    --bind 0.0.0.0:"${PORT:-8080}" \
    --workers 1 \
    --threads 4 \
    --timeout 120 \
    --worker-class gthread \
    "dashboard.app:server"
