FROM ubuntu:rolling

ENV DEBIAN_FRONTEND=noninteractive
ENV CLOAKBROWSER_AUTO_UPDATE=false
ENV PYTHONUNBUFFERED=1

# 让 ghcr.io 上的包自动关联到本仓库（同时保证 GITHUB_TOKEN 有推送权限）
LABEL org.opencontainers.image.source="https://github.com/AshenOneYe/CloudflareBypassForScraping"
LABEL org.opencontainers.image.description="CloudflareBypassForScraping server image (patched fork)"
LABEL org.opencontainers.image.licenses="MIT"

USER root
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-venv \
    wget \
    curl \
    ca-certificates \
    xvfb \
    fonts-liberation \
    fonts-noto-color-emoji \
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
    libpango-1.0-0 \
    libcairo2 \
    libasound2t64 \
    libatspi2.0-0 \
    libx11-6 \
    libxcb1 \
    libxext6 \
    libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN chmod +x /app/docker-entrypoint.sh
RUN chown -R ubuntu:ubuntu /app

USER ubuntu

RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r server_requirements.txt

# Download the patched stealth Chromium into the ubuntu user's cache
RUN python3 -c "import cloakbrowser; print(cloakbrowser.ensure_binary())"

# geoip=True is used for every proxied launch, so bake the ~70 MB GeoLite2 database
# in as well: containers that reach the internet only through a proxy cannot
# download it from GitHub at runtime, and without it every launch fails with
# "GeoIP resolution failed: GeoIP database is unavailable".
RUN python3 scripts/fetch_geoip_db.py

# Browser must run headed for managed Turnstile; the entrypoint provides Xvfb
CMD ["/app/docker-entrypoint.sh"]
