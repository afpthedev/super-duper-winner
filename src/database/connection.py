import os
import logging
from contextlib import contextmanager
from typing import Generator, Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from .models import Base
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Veritabanı bağlantı ve oturum yöneticisi"""

    def __init__(self, database_url: str | None = None):
        """DatabaseManager'ı başlatır."""
        if database_url is None:
            database_url = self._get_database_url()

        self.database_url = database_url
        self.engine = None
        self.SessionLocal: sessionmaker | None = None

        self._setup_database()

    def _get_database_url(self) -> str:
        """Çevre değişkenlerinden veya ayarlardan veritabanı URL'sini alır."""
        explicit_url = os.getenv("DATABASE_URL")
        if explicit_url:
            return explicit_url

        settings = get_settings()

        db_host = os.getenv("DB_HOST", settings.database.host)
        db_port = os.getenv("DB_PORT", str(settings.database.port))
        db_name = os.getenv("DB_NAME", settings.database.name)
        db_user = os.getenv("DB_USER", settings.database.user)
        db_password = os.getenv("DB_PASSWORD", settings.database.password)

        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    def _setup_database(self) -> None:
        """Veritabanı bağlantısını ve oturum fabrikasını ayarlar."""
        try:
            self.engine = create_engine(
                self.database_url,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                echo=os.getenv("DB_ECHO", "false").lower() == "true",
                future=True,
            )

            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine,
            )

            logger.info("Veritabanı bağlantısı başarıyla kuruldu")

        except Exception as exc:  # pragma: no cover - bağlantı hataları
            logger.error("Veritabanı bağlantısı kurulamadı: %s", exc)
            raise

    def create_tables(self) -> None:
        """Tüm tabloları oluşturur."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Veritabanı tabloları başarıyla oluşturuldu")
        except Exception as exc:  # pragma: no cover - schema hataları
            logger.error("Tablolar oluşturulamadı: %s", exc)
            raise

    def drop_tables(self) -> None:
        """Tüm tabloları siler."""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.info("Veritabanı tabloları başarıyla silindi")
        except Exception as exc:
            logger.error("Tablolar silinemedi: %s", exc)
            raise

    def get_session(self) -> Session:
        """Yeni bir veritabanı oturumu döndürür."""
        if self.SessionLocal is None:
            raise RuntimeError("Database session factory is not initialised")
        return self.SessionLocal()

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """Veritabanı oturumu için context manager."""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as exc:
            session.rollback()
            logger.error("Veritabanı işlemi başarısız: %s", exc)
            raise
        finally:
            session.close()

    def test_connection(self) -> bool:
        """Veritabanı bağlantısını test eder."""
        if self.engine is None:
            return False
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                return result.fetchone()[0] == 1
        except Exception as exc:
            logger.error("Veritabanı bağlantı testi başarısız: %s", exc)
            return False

    def close(self) -> None:
        """Veritabanı bağlantısını kapatır."""
        if self.engine:
            self.engine.dispose()
            logger.info("Veritabanı bağlantısı kapatıldı")


# Global veritabanı yöneticisi instance'ı
_db_manager: DatabaseManager | None = None


def get_db_manager() -> DatabaseManager:
    """Global veritabanı yöneticisini döndürür."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def get_db_session() -> Session:
    """Yeni bir veritabanı oturumu döndürür."""
    return get_db_manager().get_session()


@contextmanager
def get_db_session_context() -> Generator[Session, None, None]:
    """Veritabanı oturumu için context manager."""
    with get_db_manager().session_scope() as session:
        yield session


def get_db_session_dependency() -> Iterator[Session]:
    """FastAPI bağımlılığı için oturum sağlayıcı."""
    session = get_db_manager().get_session()
    try:
        yield session
    finally:
        session.close()


def init_database() -> None:
    """Veritabanını başlatır ve tabloları oluşturur."""
    manager = get_db_manager()

    if not manager.test_connection():
        raise ConnectionError("Veritabanına bağlanılamadı")

    manager.create_tables()
    logger.info("Veritabanı başarıyla başlatıldı")


if __name__ == "__main__":  # pragma: no cover - manuel testler
    logging.basicConfig(level=logging.INFO)

    try:
        init_database()
        print("Veritabanı başarıyla başlatıldı!")

        with get_db_session_context() as session:
            result = session.execute(text("SELECT COUNT(*) FROM teams"))
            count = result.fetchone()[0]
            print(f"Teams tablosunda {count} kayıt var")

    except Exception as exc:  # pragma: no cover - manuel testler
        print(f"Hata: {exc}")
