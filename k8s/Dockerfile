FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir \
    -r requirements.txt \
    kopf[kubernetes]==1.37.2 \
    prometheus-client==0.18.0 \
    flask-cors==4.0.0

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 esddns && \
    chown -R esddns:esddns /app

# Create log directory
RUN mkdir -p /app/logs && chown -R esddns:esddns /app/logs

USER esddns

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:51339/ || exit 1

# Run kopf operator and Flask service
CMD ["kopf", "run", "--liveness=http://0.0.0.0:8080/healthz", "k8s/esddns_operator.py"]
