FROM python:3.11-slim

# Avoid prompts and set workdir
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/usr/local/bin:${PATH}"

WORKDIR /app

# System deps that help some clients; keep minimal
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better cache
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools wheel \
    && pip install -r /app/requirements.txt

# Copy the app
COPY core /app/core
COPY ossc.py /app/ossc.py

# Default to running the CLI directly
ENTRYPOINT ["python", "/app/ossc.py"]
CMD ["-h"]

