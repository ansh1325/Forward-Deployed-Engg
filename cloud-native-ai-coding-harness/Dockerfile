FROM python:3.12-slim

# System tools & build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Pre-warm pip and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and control plane
COPY . .

# Non-root user for isolated sandbox security
RUN useradd -m -u 1000 harnessuser && chown -R harnessuser:harnessuser /app
USER harnessuser

EXPOSE 8000

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
