-- FBRef Veritabanı Başlangıç Scripti
-- Bu script PostgreSQL konteynerı başlatıldığında otomatik olarak çalışır

-- Veritabanı encoding'ini kontrol et
SELECT current_setting('server_encoding') as server_encoding;

-- Gerekli extension'ları yükle
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Performans için bazı ayarlar
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
-- ALTER SYSTEM SET pg_stat_statements.track = 'all';

-- Veritabanı kullanıcısı için ek yetkiler (gerekirse)
-- GRANT ALL PRIVILEGES ON DATABASE fbref_db TO postgres;

-- Başlangıç verisi ekle (opsiyonel)
-- Örnek sezonlar
INSERT INTO seasons (name, start_year, end_year, is_active) VALUES 
    ('2024-2025', 2024, 2025, true),
    ('2023-2024', 2023, 2024, false),
    ('2022-2023', 2022, 2023, false)
ON CONFLICT (name) DO NOTHING;

-- Log tablosu için index'ler (performans için)
-- Bu index'ler SQLAlchemy tarafından otomatik oluşturulacak, 
-- ancak manuel olarak da eklenebilir

-- Başarılı başlatma mesajı
DO $$
BEGIN
    RAISE NOTICE 'FBRef veritabanı başarıyla başlatıldı!';
    RAISE NOTICE 'Veritabanı: %', current_database();
    RAISE NOTICE 'Kullanıcı: %', current_user;
    RAISE NOTICE 'Zaman: %', now();
END $$;
