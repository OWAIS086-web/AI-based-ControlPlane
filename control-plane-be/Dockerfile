FROM python:3.12-slim

ARG APP_VERSION=dev
ENV APP_VERSION=$APP_VERSION

WORKDIR /app

# System deps: Node.js (for Prisma CLI) + build tools + LibreOffice (xlsx→pdf)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libreoffice \
    libfontconfig1 \
    fonts-liberation \
    fonts-noto-cjk \
    tesseract-ocr \
    tesseract-ocr-eng \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Generate Prisma Python client
RUN prisma generate

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

COPY prometheus/prometheus.yml /etc/prometheus/prometheus.yml
COPY grafana/provisioning /etc/grafana/provisioning
COPY grafana/dashboards /etc/grafana/dashboards

ENTRYPOINT ["/entrypoint.sh"]
