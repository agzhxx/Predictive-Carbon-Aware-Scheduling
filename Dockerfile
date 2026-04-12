FROM python:3.11-slim

WORKDIR /app

# Force Python to print output in real-time (no buffering)
ENV PYTHONUNBUFFERED=1

# Install system dependencies for PyTorch and matplotlib
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire project
COPY . .

# Unzip Azure dataset if the zip exists and the folder doesn't
RUN if [ -f data/azure_dataset.zip ] && [ ! -d data/azure_dataset ]; then \
    apt-get update && apt-get install -y --no-install-recommends unzip && \
    unzip data/azure_dataset.zip -d data/azure_dataset && \
    rm -rf /var/lib/apt/lists/*; \
    fi

# Default: run the evaluation suite
CMD ["python3", "evaluation/runner.py"]
