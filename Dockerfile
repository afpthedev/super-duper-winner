# Python 3.11 slim imajını kullan
FROM python:3.11-slim

# Metadata
LABEL maintainer="FBRef Scraper Team"
LABEL description="FBRef futbolcu veri çekme uygulaması"
LABEL version="1.0.0"

# Çalışma dizinini ayarla
WORKDIR /app

# Sistem paketlerini güncelle ve gerekli paketleri yükle
RUN apt-get update && apt-get install -y \
    # Chrome ve Selenium için gerekli paketler
    wget \
    gnupg \
    unzip \
    curl \
    # PostgreSQL client
    postgresql-client \
    # Sistem araçları
    procps \
    && rm -rf /var/lib/apt/lists/*

# Google Chrome'u yükle
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# ChromeDriver'ı yükle
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d. -f1-3) \
    && CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION}") \
    && wget -O /tmp/chromedriver.zip "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip" \
    && unzip /tmp/chromedriver.zip -d /tmp/ \
    && mv /tmp/chromedriver /usr/local/bin/chromedriver \
    && chmod +x /usr/local/bin/chromedriver \
    && rm /tmp/chromedriver.zip

# Python bağımlılıklarını yükle
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Uygulama kodunu kopyala
COPY . .

# Logs dizinini oluştur
RUN mkdir -p logs

# Çevre değişkenlerini ayarla
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

# Chrome için güvenlik ayarları
ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROME_PATH=/usr/bin/google-chrome

# Uygulama kullanıcısı oluştur (güvenlik için)
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# Port açma (API servisi)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from src.database.connection import get_db_manager; print('OK' if get_db_manager().test_connection() else exit(1))"

# Varsayılan komut API sunucusunu çalıştırır
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]