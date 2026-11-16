import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key-change-me"
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or (
        "mysql+pymysql://{user}:{password}@{host}:{port}/{name}".format(
            user=os.environ.get("DB_USER", "ecotrack_user"),
            password=os.environ.get("DB_PASSWORD", "change-me"),
            host=os.environ.get("DB_HOST", "localhost"),
            port=os.environ.get("DB_PORT", "3306"),
            name=os.environ.get("DB_NAME", "ecotrack"),
        )
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 5242880))
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "app/static/uploads")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    LOGGING_LEVEL = os.environ.get("LOGGING_LEVEL", "INFO")

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///ecotrack_test.db"
    WTF_CSRF_ENABLED = False
    SERVER_NAME = "localhost.localdomain"


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
