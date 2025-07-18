FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create directories
RUN mkdir -p /config /var/log

# Create non-root user
RUN useradd -m -s /bin/bash cbus && \
    chown -R cbus:cbus /app /config /var/log

# Switch to non-root user
USER cbus

# Expose port for health check
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import asyncio; import sys; sys.exit(0)"

# Set environment variables
ENV PYTHONPATH=/app
ENV CONFIG_PATH=/config/config.yaml

# Command to run the application
CMD ["python", "main.py", "--config", "/config/config.yaml"] 