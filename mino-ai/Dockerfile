# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    build-essential \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-xlib-2.0-0 \
    libffi-dev \
    libxml2 \
    libxslt1.1 \
    libjpeg-dev \
    zlib1g-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip for better timeout handling
RUN pip install --upgrade pip

# Install Python dependencies with increased timeout and retries
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout=300 --retries=5 -r requirements.txt

COPY .env.prod .env.prod
COPY .env.dev .env.dev

# Copy project
COPY . .

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 5000

# Run the application with gunicorn
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "-b", "0.0.0.0:5000", "--log-level", "info", "--access-logfile", "-", "--error-logfile", "-", "app:create_app('prod')"]