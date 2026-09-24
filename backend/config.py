import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root directory
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """Base configuration class with common settings."""
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-replace-in-production")
    
    # SQLAlchemy configuration
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,     # Test connections for liveness upon checkout
        "pool_recycle": 280,       # Recycle connections before MySQL default timeout (300s/8h)
    }

    # CORS settings
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

    # File Upload settings
    UPLOAD_FOLDER = Path(os.getenv("UPLOAD_FOLDER", BASE_DIR / "uploads" / "resumes"))
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB max file size
    ALLOWED_EXTENSIONS = {"pdf"}

    @classmethod
    def get_database_uri(cls):
        """
        Retrieves and formats the database URI from the DATABASE_URL environment variable.
        Supports Cloud SQL and standard MySQL connection strings.
        """
        database_url = os.getenv("DATABASE_URL", "").strip()
        if not database_url:
            return "mysql+pymysql://root@127.0.0.1:3306/placement_db"

        # Standardize MySQL driver URL to pymysql if mysql:// is supplied
        if database_url.startswith("mysql://"):
            return "mysql+pymysql://" + database_url[len("mysql://"):]
        if database_url.startswith("postgres://"):
            return "postgresql://" + database_url[len("postgres://"):]

        return database_url


class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = Config.get_database_uri()


class TestingConfig(Config):
    """Testing environment configuration."""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = Config.get_database_uri()


class ProductionConfig(Config):
    """Production environment configuration."""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = Config.get_database_uri()


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
