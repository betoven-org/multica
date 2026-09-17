FROM python:3.12-bookworm

# Install system deps for Playwright (Chromium needs these)
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget curl libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libexpat1 libxcb1 libxkbcommon0 libx11-6 \
    libxcomposite1 libxdamage1 libxext6 libxfixes3 libxrandr2 libgbm1 \
    libpango-1.0-0 libcairo2 libasound2t64 libatspi2.0-0 fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium (deps already installed above)
RUN playwright install chromium

# Copy app code
COPY . .

# Mem0 data dir
RUN mkdir -p /data/memory
ENV ODUS_MEMORY_DIR=/data/memory

EXPOSE 8090

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8090"]
