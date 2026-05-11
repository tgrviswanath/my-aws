# ─── Stage 1: Builder ─────────────────────────────────────────────────────────
# Install dependencies in a separate stage to keep the final image clean
FROM python:3.11-slim AS builder

WORKDIR /build

# Copy only requirements first — Docker caches this layer
# If requirements.txt doesn't change, this layer is reused on rebuild
COPY app/requirements.txt .

RUN pip install --no-cache-dir --user -r requirements.txt


# ─── Stage 2: Runtime ─────────────────────────────────────────────────────────
# Start fresh from a minimal base image
FROM python:3.11-slim AS runtime

# Security: create a non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY app/ .

# Set ownership
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Environment variables with sensible defaults
ENV PORT=5000 \
    APP_ENV=production \
    APP_VERSION=1.0.0 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/appuser/.local/bin:$PATH"

EXPOSE 5000

# Health check — Docker monitors this every 30s
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:$PORT/health')"

# Use gunicorn for production (not Flask dev server)
ENTRYPOINT ["gunicorn"]
CMD ["--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "60", "app:app"]
