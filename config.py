import os
from sqlalchemy.engine import URL

from env_loader import load_environment

# Load environment configuration (.env and/or process environment) before any
# configuration class is initialized and before the database engine is created.
# Precedence (documented and deterministic):
#   1. Process environment variables (highest; never overwritten by .env)
#   2. Values from the discovered .env file
#   3. Hard-coded defaults in this module (lowest)
# load_dotenv is invoked with override=False so an existing process variable
# always wins over a .env value.
load_environment()

REQUIRED_DB_VARS = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD")


def _missing_db_vars():
    return [v for v in REQUIRED_DB_VARS if not os.environ.get(v)]


def build_database_uri():
    """Build the SQLAlchemy database URL from environment variables.

    `DATABASE_URL` takes precedence when set. Otherwise the URL is built from
    `DB_HOST`/`DB_PORT`/`DB_NAME`/`DB_USER`/`DB_PASSWORD` using
    `SQLAlchemy URL.create()` so passwords containing special characters are
    encoded correctly instead of being concatenated raw into a connection
    string.

    Returns None when required values are missing or invalid so the caller can
    report a clear configuration error instead of a misleading connection
    failure. Never substitutes a placeholder password.
    """
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        return database_url
    if _missing_db_vars():
        return None
    try:
        port = int(os.environ["DB_PORT"])
    except (TypeError, ValueError):
        return None
    return URL.create(
        drivername="mysql+pymysql",
        username=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ["DB_HOST"],
        port=port,
        database=os.environ["DB_NAME"],
    )


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = build_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 5242880))
    # Private uploads live outside the public static directory.
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "instance/uploads")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    LOGGING_LEVEL = os.environ.get("LOGGING_LEVEL", "INFO")

    @classmethod
    def init_app(cls, app):
        cls._validate_database_configuration(app)

    @classmethod
    def _validate_database_configuration(cls, app):
        """Fail safely with a clear error when the database is not configured."""
        uri = app.config.get("SQLALCHEMY_DATABASE_URI")
        if uri is None:
            missing = _missing_db_vars()
            detail = (
                ", ".join(missing)
                if missing
                else "DB_PORT must be an integer or DATABASE_URL must be set"
            )
            raise RuntimeError(
                "EcoTrack is not configured to connect to the database.\n"
                "Missing or invalid required configuration: "
                + detail
                + "\nSet DB_HOST, DB_PORT, DB_NAME, DB_USER and DB_PASSWORD "
                "(or DATABASE_URL) in your .env file or environment variables."
            )


class DevelopmentConfig(Config):
    DEBUG = True

    @classmethod
    def init_app(cls, app):
        super().init_app(app)
        if not app.config.get("SECRET_KEY"):
            app.config["SECRET_KEY"] = "dev-secret-key-change-me"
            app.logger.warning(
                "Development running with fallback SECRET_KEY. "
                "Set a strong SECRET_KEY environment variable before any production deployment."
            )


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True

    @classmethod
    def init_app(cls, app):
        super().init_app(app)
        cls._validate_production_secrets(app)

    @classmethod
    def _validate_production_secrets(cls, app):
        """Fail safely when required production configuration is missing."""
        secret = os.environ.get("SECRET_KEY")
        if not secret or len(secret) < 16:
            raise RuntimeError(
                "Production configuration requires a strong SECRET_KEY "
                "environment variable (at least 16 characters). "
                "Set SECRET_KEY before deploying."
            )
        app.config["SECRET_KEY"] = secret


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///ecotrack_test.db"
    WTF_CSRF_ENABLED = False
    SERVER_NAME = "localhost.localdomain"
    SECRET_KEY = os.environ.get("SECRET_KEY") or "test-secret-key-do-not-use-in-production"


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
