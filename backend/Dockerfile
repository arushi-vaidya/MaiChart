# Backend Dockerfile - Docker-only optimized
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variable for Docker detection
ENV RUNNING_IN_DOCKER=true
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Install system dependencies including ffmpeg and curl
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/uploads /app/transcripts /app/chunks /app/logs

# Expose port
EXPOSE 5001

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5001/health || exit 1

# Default command - runs backend server
CMD ["python", "app.py"]