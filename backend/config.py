import os
from urllib.parse import quote_plus
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
        Builds the database URI.
        Prioritizes DATABASE_URL if explicitly set.
        Otherwise builds standard MySQL URI using individual parameters.
        """
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            # Accept standard MySQL URLs and use the installed PyMySQL driver.
            if database_url.startswith("mysql://"):
                return "mysql+pymysql://" + database_url[len("mysql://"):]
            if not database_url.startswith("mysql+pymysql://"):
                raise ValueError("DATABASE_URL must use mysql:// or mysql+pymysql://")
            return database_url

        user = os.getenv("DB_USER", "root")
        password = quote_plus(os.getenv("DB_PASSWORD", ""))
        host = os.getenv("DB_HOST", "127.0.0.1")
        port = os.getenv("DB_PORT", "3306")
        db_name = os.getenv("DB_NAME", "placement_db")

        # PyMySQL driver is used: mysql+pymysql://<user>:<password>@<host>:<port>/<db_name>
        if password:
            return f"mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}"
        return f"mysql+pymysql://{user}@{host}:{port}/{db_name}"


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
