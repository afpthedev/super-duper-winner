import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager
from typing import Generator

from .models import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Veritabanı bağlantı ve oturum yöneticisi"""
    
    def __init__(self, database_url: str = None):
        """
        DatabaseManager'ı başlatır.
        
        Args:
            database_url: Veritabanı bağlantı URL'si
        """
        if database_url is None:
            database_url = self._get_database_url()
        
        self.database_url = database_url
        self.engine = None
        self.SessionLocal = None
        
        self._setup_database()
    
    def _get_database_url(self) -> str:
        """Çevre değişkenlerinden veritabanı URL'sini alır."""
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'fbref_db')
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', 'password')
        
        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    def _setup_database(self):
        """Veritabanı bağlantısını ve oturum fabrikasını ayarlar."""
        try:
            self.engine = create_engine(
                self.database_url,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                echo=os.getenv('DB_ECHO', 'false').lower() == 'true'
            )
            
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            logger.info("Veritabanı bağlantısı başarıyla kuruldu")
            
        except Exception as e:
            logger.error(f"Veritabanı bağlantısı kurulamadı: {str(e)}")
            raise
    
    def create_tables(self):
        """Tüm tabloları oluşturur."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Veritabanı tabloları başarıyla oluşturuldu")
        except Exception as e:
            logger.error(f"Tablolar oluşturulamadı: {str(e)}")
            raise
    
    def drop_tables(self):
        """Tüm tabloları siler."""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.info("Veritabanı tabloları başarıyla silindi")
        except Exception as e:
            logger.error(f"Tablolar silinemedi: {str(e)}")
            raise
    
    def get_session(self) -> Session:
        """Yeni bir veritabanı oturumu döndürür."""
        return self.SessionLocal()
    
    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        Veritabanı oturumu için context manager.
        Otomatik commit/rollback işlemleri yapar.
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Veritabanı işlemi başarısız: {str(e)}")
            raise
        finally:
            session.close()
    
    def test_connection(self) -> bool:
        """Veritabanı bağlantısını test eder."""
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                return result.fetchone()[0] == 1
        except Exception as e:
            logger.error(f"Veritabanı bağlantı testi başarısız: {str(e)}")
            return False
    
    def close(self):
        """Veritabanı bağlantısını kapatır."""
        if self.engine:
            self.engine.dispose()
            logger.info("Veritabanı bağlantısı kapatıldı")


# Global veritabanı yöneticisi instance'ı
db_manager = None


def get_db_manager() -> DatabaseManager:
    """Global veritabanı yöneticisini döndürür."""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
    return db_manager


def get_db_session() -> Session:
    """Yeni bir veritabanı oturumu döndürür."""
    return get_db_manager().get_session()


@contextmanager
def get_db_session_context() -> Generator[Session, None, None]:
    """Veritabanı oturumu için context manager."""
    with get_db_manager().session_scope() as session:
        yield session


def init_database():
    """Veritabanını başlatır ve tabloları oluşturur."""
    manager = get_db_manager()
    
    # Bağlantıyı test et
    if not manager.test_connection():
        raise ConnectionError("Veritabanına bağlanılamadı")
    
    # Tabloları oluştur
    manager.create_tables()
    
    logger.info("Veritabanı başarıyla başlatıldı")


if __name__ == "__main__":
    # Test için
    logging.basicConfig(level=logging.INFO)
    
    try:
        init_database()
        print("Veritabanı başarıyla başlatıldı!")
        
        # Bağlantı testi
        with get_db_session_context() as session:
            result = session.execute(text("SELECT COUNT(*) FROM teams"))
            count = result.fetchone()[0]
            print(f"Teams tablosunda {count} kayıt var")
            
    except Exception as e:
        print(f"Hata: {str(e)}")