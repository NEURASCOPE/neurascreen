FROM python:3.12-slim

LABEL maintainer="NEURASCOPE <contact@neurascope.ai>"
LABEL description="NeuraScreen — Automated demo video generator (headless)"

# System dependencies: ffmpeg, Xvfb, and Playwright browser deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    xvfb \
    xauth \
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libgtk-3-0 \
    libx11-xcb1 \
    libxshmfence1 \
    fonts-liberation \
    fonts-noto-color-emoji \
    pulseaudio \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install NeuraScreen
COPY pyproject.toml README.md LICENSE ./
COPY neurascreen/ ./neurascreen/
RUN pip install --no-cache-dir ".[all]"

# Install Playwright Chromium
RUN playwright install chromium

# Copy examples and entrypoint
COPY examples/ ./examples/
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Output and temp directories
RUN mkdir -p /app/output /app/temp /app/logs

# Default env for headless operation
ENV BROWSER_HEADLESS=true
ENV DISPLAY=:99
ENV OUTPUT_DIR=/app/output
ENV TEMP_DIR=/app/temp
ENV LOGS_DIR=/app/logs

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["--help"]
