FROM python:3.12-slim

WORKDIR /app

# Install system dependencies first (better layer caching)
# WeasyPrint needs: pango, cairo, gdk-pixbuf, fontconfig, harfbuzz
# OpenCV needs: libgl1, libglib2.0
# psycopg2 needs: libpq-dev
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    ffmpeg \
    curl \
    build-essential \
    libpq-dev \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libcairo2-dev \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    libglib2.0-0 \
    libgl1 \
    libglib2.0-dev \
    shared-mime-info \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install Poetry and RunPod
RUN pip install --no-cache-dir poetry runpod

# Copy only pyproject.toml and poetry.lock (if it exists)
COPY pyproject.toml poetry.lock* ./

# Install project dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root --only main

# Cache-bust: ensures code changes are always picked up
# (system deps + poetry install above stay cached for speed)
ARG CACHEBUST=1

# Copy the rest of the application code
COPY . .

# Install custom PhonicsMaker fonts for WeasyPrint/Pango
RUN mkdir -p /usr/share/fonts/truetype/phonicsmaker \
    && cp static/fonts/*.ttf /usr/share/fonts/truetype/phonicsmaker/ \
    && fc-cache -f

# Ensure proper permissions
RUN chown -R root:root /app && \
    chmod -R 755 /app

# Set environment variables for RunPod
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production
ENV RUNPOD_DEBUG_LEVEL=INFO

# These are needed for systems with GPUs for the pdf processing
ENV OPENBLAS_NUM_THREADS=1 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1

# RunPod serverless doesn't use EXPOSE or specific PORT
# The handler will be called directly by RunPod

# Run the RunPod handler with wrapper for better error handling
CMD ["python", "-u", "runpod_wrapper.py"]