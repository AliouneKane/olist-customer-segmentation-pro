#!/bin/sh
# Streamlit startup for the Olist Segmentation SaaS Dashboard.
#
# PORT is injected by Cloud Run at container startup; defaults to 8080.
exec streamlit run streamlit_app/main.py \
    --server.port "${PORT:-8080}" \
    --server.address 0.0.0.0 \
    --server.headless true \
    --server.enableCORS false \
    --server.enableXsrfProtection false
