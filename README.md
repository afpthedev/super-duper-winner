# FBRef Futbolcu Veri Çekme Sistemi

Bu proje, [FBRef](https://fbref.com) sitesinden futbolcu verilerini otomatik olarak çeken ve PostgreSQL veritabanında saklayan bir Docker tabanlı sistemdir. <mcreference link="https://medium.com/@henrik.schjoth/scraping-fbref-creating-a-pipeline-f5c9c23ba9da" index="0">0</mcreference> Henrik Schjøth'ün makalesinden ilham alınarak geliştirilmiştir.

## 🚀 Özellikler

- **Web Scraping**: BeautifulSoup ve Selenium kullanarak FBRef'ten veri çekme
- **Veritabanı**: PostgreSQL ile güvenli veri saklama
- **Docker**: Kolay deployment ve taşınabilirlik
- **Modüler Yapı**: Genişletilebilir ve sürdürülebilir kod yapısı
- **Loglama**: Detaylı işlem kayıtları
- **Konfigürasyon**: Esnek çevre değişkeni yönetimi
- **Modern UI**: Ant Design bileşenleriyle hazırlanmış React dashboard

## 📊 Çekilen Veriler

Sistem aşağıdaki futbolcu verilerini toplar:

- **Temel Bilgiler**: Ad-soyad, pozisyon, yaş, takım
- **Sezon İstatistikleri**: Gol, asist, oynadığı maç sayısı
- **Gelişmiş Metrikler**: xG, xA, pas tamamlama oranı
- **Savunma İstatistikleri**: Müdahale, top kesme, blok
- **Maç Bazlı Veriler**: Her maç için detaylı performans

## 🛠️ Kurulum

### Gereksinimler

- Docker ve Docker Compose
- Git
- En az 2GB RAM
- 5GB disk alanı

### Hızlı Başlangıç

1. **Projeyi klonlayın:**
```bash
git clone <repository-url>
cd FBREF
```

2. **Çevre değişkenlerini ayarlayın:**
```bash
cp .env.example .env
# .env dosyasını ihtiyaçlarınıza göre düzenleyin
```

3. **Docker ile çalıştırın:**
```bash
# Tüm servisleri başlat (PostgreSQL + API + React arayüzü)
docker-compose up -d

# Sadece API ve veritabanı servisleri
docker-compose up -d postgres backend
```

4. **Logları kontrol edin:**
```bash
docker-compose logs -f backend
```

5. **Web arayüzünü açın:**
```
http://localhost:5173
```

API servisleri varsayılan olarak `http://localhost:8000` adresinden erişilebilir.

## 🎯 Kullanım

### Farklı Modlar

#### Test Modu (Varsayılan)
Tek takım için test çalıştırır:
```bash
docker-compose run --rm backend python main.py --mode test
```

#### Tam Pipeline
Tüm ligler için veri çeker:
```bash
docker-compose run --rm backend python main.py --mode full
```

#### Tek Takım
Belirli bir takım için veri çeker:
```bash
docker-compose run --rm backend python main.py --mode team --team-url "https://fbref.com/en/squads/18bb7c10/Arsenal-Stats"
```

#### Özel Sezon
Farklı sezon için:
```bash
docker-compose run --rm backend python main.py --mode full --season "2023-2024"
```

### Yerel Çalıştırma

Docker kullanmadan yerel olarak çalıştırmak için:

```bash
# Bağımlılıkları yükle
pip install -r requirements.txt

# PostgreSQL'i başlat (yerel veya Docker)
docker run -d --name postgres -e POSTGRES_PASSWORD=password -p 5432:5432 postgres:15

# Uygulamayı çalıştır
python main.py --mode test
```

## 🗄️ Veritabanı Yönetimi

### pgAdmin ile Erişim

pgAdmin web arayüzü ile veritabanını yönetebilirsiniz:

```bash
# pgAdmin'i başlat
docker-compose --profile admin up -d pgadmin

# Tarayıcıda açın: http://localhost:8080
# Email: admin@fbref.com
# Şifre: admin123
```

### Doğrudan PostgreSQL Erişimi

```bash
# Konteyner içinden
docker-compose exec postgres psql -U postgres -d fbref_db

# Yerel istemci ile
psql -h localhost -U postgres -d fbref_db
```

### Veritabanı Şeması

Temel tablolar:
- `teams`: Takım bilgileri
- `players`: Oyuncu bilgileri  
- `seasons`: Sezon bilgileri
- `player_stats`: Oyuncu istatistikleri
- `match_logs`: Maç bazlı veriler
- `scraping_logs`: İşlem logları

## ⚙️ Konfigürasyon

### Çevre Değişkenleri

Önemli ayarlar:

```bash
# Veritabanı
DB_HOST=postgres
DB_NAME=fbref_db
DB_USER=postgres
DB_PASSWORD=password

# Scraping
SCRAPING_DELAY=2.0          # İstekler arası bekleme (saniye)
SCRAPING_HEADLESS=true      # Tarayıcı görünmez mod
SCRAPING_MAX_RETRIES=3      # Maksimum deneme sayısı

# Loglama
LOG_LEVEL=INFO
LOG_FILE_PATH=logs/app.log
```

### Docker Compose Profilleri

```bash
# Sadece temel servisler
docker-compose up -d

# Admin araçları ile
docker-compose --profile admin up -d

# Cache ile (Redis)
docker-compose --profile cache up -d
```

## 📁 Proje Yapısı

```
FBREF/
├── src/
│   ├── scraper/           # Web scraping modülleri
│   ├── database/          # Veritabanı modelleri ve bağlantı
│   └── config/            # Konfigürasyon ayarları
├── init-scripts/          # Veritabanı başlangıç scriptleri
├── logs/                  # Uygulama logları
├── docker-compose.yml     # Docker servis tanımları
├── Dockerfile            # Uygulama konteyner tanımı
├── requirements.txt      # Python bağımlılıkları
├── main.py              # Ana uygulama dosyası
└── README.md            # Bu dosya
```

## 🔧 Geliştirme

### Yerel Geliştirme Ortamı

```bash
# Sanal ortam oluştur
python -m venv venv
source venv/bin/activate  # Linux/Mac
# veya
venv\\Scripts\\activate   # Windows

# Bağımlılıkları yükle
pip install -r requirements.txt

# Geliştirme bağımlılıkları
pip install pytest black flake8 mypy
```

### Kod Kalitesi

```bash
# Kod formatlama
black src/ main.py

# Linting
flake8 src/ main.py

# Type checking
mypy src/ main.py

# Testler
pytest tests/
```

### Yeni Özellik Ekleme

1. `src/` altında uygun modülü düzenleyin
2. Gerekirse yeni veritabanı modeli ekleyin
3. Testler yazın
4. Docker imajını yeniden build edin

## 🚨 Sorun Giderme

### Yaygın Sorunlar

**1. Chrome/ChromeDriver Hatası:**
```bash
# Docker konteynerını yeniden build edin
docker-compose build --no-cache fbref-scraper
```

**2. Veritabanı Bağlantı Hatası:**
```bash
# PostgreSQL'in çalıştığını kontrol edin
docker-compose ps postgres
docker-compose logs postgres
```

**3. Bellek Yetersizliği:**
```bash
# Docker bellek limitini artırın
# docker-compose.yml'de deploy.resources.limits.memory ekleyin
```

**4. Rate Limiting:**
```bash
# SCRAPING_DELAY değerini artırın
export SCRAPING_DELAY=5.0
```

### Logları İnceleme

```bash
# Tüm servis logları
docker-compose logs

# Sadece scraper logları
docker-compose logs fbref-scraper

# Canlı log takibi
docker-compose logs -f fbref-scraper
```

## 📈 Performans Optimizasyonu

### Scraping Hızı

- `SCRAPING_DELAY` değerini azaltın (dikkatli olun)
- `MAX_WORKERS` sayısını artırın
- Headless modu kullanın

### Veritabanı

- Uygun index'ler ekleyin
- Batch insert kullanın
- Connection pooling ayarlayın

### Docker

- Multi-stage build kullanın
- Gereksiz paketleri kaldırın
- Volume'ları optimize edin

## 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Commit yapın (`git commit -m 'Add amazing feature'`)
4. Push yapın (`git push origin feature/amazing-feature`)
5. Pull Request açın

## 📄 Lisans

Bu proje MIT lisansı altında lisanslanmıştır. Detaylar için `LICENSE` dosyasına bakın.

## 🙏 Teşekkürler

- <mcreference link="https://medium.com/@henrik.schjoth/scraping-fbref-creating-a-pipeline-f5c9c23ba9da" index="0">0</mcreference> Henrik Schjøth'ün FBRef scraping makalesine
- FBRef.com'a veri sağladığı için
- Açık kaynak topluluğuna

## 📞 İletişim

Sorularınız için:
- Issue açın
- Pull request gönderin
- Dokümantasyonu inceleyin

---

**Not**: Bu araç eğitim amaçlıdır. FBRef'in robots.txt ve kullanım koşullarına uygun şekilde kullanın. Aşırı istek göndermeyin ve sitenin performansını etkilemeyin.