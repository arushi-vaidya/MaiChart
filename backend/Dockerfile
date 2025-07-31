# FastAPI Backend Dockerfile - Production ready
FROM python:3.11-slim

# Install system dependencies including FFmpeg and curl for health checks
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with verbose output
RUN pip install --no-cache-dir -v -r requirements.txt

# Copy application files
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p uploads logs transcripts chunks && \
    chmod 755 uploads logs transcripts chunks

# Create non-root user for security
RUN useradd -m -u 1001 appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 5001

# Add health check script for FastAPI
COPY --chown=appuser:appuser <<EOF /app/healthcheck.py
#!/usr/bin/env python3
import requests
import sys
import time

def health_check():
    max_retries = 5
    for i in range(max_retries):
        try:
            response = requests.get('http://localhost:5001/api/health', timeout=10)
            if response.status_code == 200:
                print("✅ Health check passed")
                sys.exit(0)
            else:
                print(f"❌ Health check failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Health check error (attempt {i+1}/{max_retries}): {e}")
            if i < max_retries - 1:
                time.sleep(5)
    
    sys.exit(1)

if __name__ == "__main__":
    health_check()
EOF

RUN chmod +x /app/healthcheck.py

# Health check with longer timeout for Docker
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=5 \
    CMD python /app/healthcheck.py

# Default command - run FastAPI with uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5001"]