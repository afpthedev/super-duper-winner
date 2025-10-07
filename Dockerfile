# Python 3.11 slim imajını kullan
FROM python:3.11-slim

# Metadata
LABEL maintainer="FBRef Scraper Team"
LABEL description="FBRef futbolcu veri çekme uygulaması"
LABEL version="1.0.0"

# Çalışma dizinini ayarla
WORKDIR /app

# Sistem paketlerini güncelle ve tüm gerekli paketleri tek seferde yükle
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    ca-certificates \
    jq \
    postgresql-client \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Chrome ve ChromeDriver kurulumu
RUN mkdir -p /etc/apt/keyrings \
    && wget -q -O /etc/apt/keyrings/google-linux-signing-key.gpg https://dl.google.com/linux/linux_signing_key.pub \
    && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-linux-signing-key.gpg] http://dl.google.com/linux/chrome/deb/ stable main" \
       > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# ChromeDriver kurulumu - Chrome versiyonuyla eşleşen
RUN CHROME_MAJOR_VERSION=$(google-chrome --version | sed 's/.*Google Chrome \([0-9]*\)\..*/\1/') \
    && echo "Chrome version: $CHROME_MAJOR_VERSION" \
    && CHROMEDRIVER_URL=$(curl -s "https://googlechromelabs.github.io/chrome-for-testing/latest-versions-per-milestone-with-downloads.json" \
       | jq -r ".milestones[\"$CHROME_MAJOR_VERSION\"].downloads.chromedriver[] | select(.platform==\"linux64\") | .url") \
    && echo "ChromeDriver URL: $CHROMEDRIVER_URL" \
    && wget -O /tmp/chromedriver.zip "${CHROMEDRIVER_URL}" \
    && unzip -d /usr/local/bin/ /tmp/chromedriver.zip \
    && mv /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver \
    && chmod +x /usr/local/bin/chromedriver \
    && rm -rf /tmp/chromedriver.zip /usr/local/bin/chromedriver-linux64 \
    && chromedriver --version

# Python bağımlılıklarını yükle
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Uygulama kodunu kopyala
COPY . .

# Logs dizinini oluştur
RUN mkdir -p logs

# Çevre değişkenlerini ayarla
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    DISPLAY=:99 \
    CHROME_BIN=/usr/bin/google-chrome \
    CHROME_PATH=/usr/bin/google-chrome

# Uygulama kullanıcısı oluştur (güvenlik için)
RUN groupadd -r appuser \
    && useradd -r -g appuser appuser \
    && chown -R appuser:appuser /app

USER appuser

# Port açma (API servisi)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from src.database.connection import get_db_manager; print('OK' if get_db_manager().test_connection() else exit(1))"

# Varsayılan komut API sunucusunu çalıştırır
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]