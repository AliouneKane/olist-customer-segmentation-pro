# ── Stage 1: builder ──────────────────────────────────────────────────────────
# Install all Python dependencies into /root/.local (user-site, no system-wide)
FROM python:3.10-slim AS builder

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --user -r requirements.txt


# ── Stage 2: runner ───────────────────────────────────────────────────────────
# Copy only the installed packages and application code — no build tools
FROM python:3.10-slim AS runner

WORKDIR /app

# Bring installed packages from the builder stage
COPY --from=builder /root/.local /root/.local

# Application source
COPY src/ ./src/
COPY streamlit_app/ ./streamlit_app/

# Pre-computed artifacts (parquets + modèles générés par les notebooks)
COPY data/processed/ ./data/processed/
COPY models/ ./models/

# Container startup script
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Ensure user-installed packages are on PATH
ENV PATH=/root/.local/bin:$PATH

# Cloud Run injects PORT; default to 8080 for local docker run
ENV PORT=8080
EXPOSE 8080

CMD ["/entrypoint.sh"]
