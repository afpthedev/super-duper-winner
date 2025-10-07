import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class DatabaseSettings(BaseSettings):
    """Veritabanı ayarları"""
    
    host: str = Field(default="localhost", env="DB_HOST")
    port: int = Field(default=5432, env="DB_PORT")
    name: str = Field(default="fbref_db", env="DB_NAME")
    user: str = Field(default="postgres", env="DB_USER")
    password: str = Field(default="password", env="DB_PASSWORD")
    echo: bool = Field(default=False, env="DB_ECHO")
    
    @property
    def url(self) -> str:
        """Veritabanı bağlantı URL'sini döndürür"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
    
    class Config:
        env_prefix = "DB_"


class ScrapingSettings(BaseSettings):
    """Web scraping ayarları"""
    
    delay_between_requests: float = Field(default=2.0, env="SCRAPING_DELAY")
    max_retries: int = Field(default=3, env="SCRAPING_MAX_RETRIES")
    timeout: int = Field(default=30, env="SCRAPING_TIMEOUT")
    headless_browser: bool = Field(default=True, env="SCRAPING_HEADLESS")
    user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        env="SCRAPING_USER_AGENT"
    )
    
    # FBRef spesifik ayarlar
    fbref_base_url: str = Field(default="https://fbref.com", env="FBREF_BASE_URL")
    default_leagues: List[str] = Field(
        default=["Premier League", "La Liga", "Bundesliga", "Serie A", "Ligue 1"],
        env="DEFAULT_LEAGUES"
    )
    default_season: str = Field(default="2024-2025", env="DEFAULT_SEASON")
    
    @validator('delay_between_requests')
    def validate_delay(cls, v):
        if v < 0.5:
            raise ValueError('Delay must be at least 0.5 seconds')
        return v
    
    class Config:
        env_prefix = "SCRAPING_"


class LoggingSettings(BaseSettings):
    """Loglama ayarları"""
    
    level: str = Field(default="INFO", env="LOG_LEVEL")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    file_path: Optional[str] = Field(default=None, env="LOG_FILE_PATH")
    max_file_size: int = Field(default=10485760, env="LOG_MAX_FILE_SIZE")  # 10MB
    backup_count: int = Field(default=5, env="LOG_BACKUP_COUNT")
    
    class Config:
        env_prefix = "LOG_"


class AppSettings(BaseSettings):
    """Genel uygulama ayarları"""
    
    app_name: str = Field(default="FBRef Scraper", env="APP_NAME")
    version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # Docker ayarları
    docker_network: str = Field(default="fbref_network", env="DOCKER_NETWORK")
    
    # Veri işleme ayarları
    batch_size: int = Field(default=100, env="BATCH_SIZE")
    max_workers: int = Field(default=4, env="MAX_WORKERS")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class Settings(BaseSettings):
    """Ana ayarlar sınıfı - tüm ayarları birleştirir"""
    
    database: DatabaseSettings = DatabaseSettings()
    scraping: ScrapingSettings = ScrapingSettings()
    logging: LoggingSettings = LoggingSettings()
    app: AppSettings = AppSettings()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Global settings instance'ını döndürür"""
    return settings


# Çevre değişkenlerini yükle
def load_env_file():
    """Çevre değişkenlerini .env dosyasından yükler"""
    from dotenv import load_dotenv
    
    env_file = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    if os.path.exists(env_file):
        load_dotenv(env_file)


# Uygulama başlatılırken çevre değişkenlerini yükle
load_env_file()