FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install necessary packages for playwright
RUN apt-get update && apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Copy files
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (chromium)
RUN playwright install chromium
RUN playwright install-deps chromium

COPY . .

# Expose port
EXPOSE 5000

# Set public mode to true by default for docker
ENV PUBLIC_MODE=true

CMD ["python", "main.py"]
