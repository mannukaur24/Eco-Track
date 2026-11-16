"""EcoTrack - Smart Waste Management System
Windows desktop launcher for the packaged EcoTrack.exe.

This launcher is the entry point of the distributed executable. It does NOT
create a duplicate Flask application: the existing application factory
(create_app in app/__init__.py) is imported and used verbatim.

Responsibilities
----------------
1. Load configuration from an external .env file located next to the
   executable or in %LOCALAPPDATA%\\EcoTrack\\.env (system environment
   variables always take precedence).
2. Import and initialise the existing Flask application via create_app().
3. Start the application with Waitress, bound exclusively to 127.0.0.1:5000,
   with Flask debug mode and the development reloader disabled.
4. Open the default browser at http://127.0.0.1:5000/.
5. Check whether port 5000 is occupied and show a useful error if so.
6. Check MySQL connectivity before starting the server and show a clear
   message when the database configuration or connectivity is invalid.
7. Write startup errors to a persistent log under
   %LOCALAPPDATA%\\EcoTrack\\logs\\ecotrack.log.
8. Handle Ctrl+C shutdown gracefully.

Writable data (logs, uploaded complaint images, local configuration) is kept
outside the PyInstaller extraction directory, under %LOCALAPPDATA%\\EcoTrack/.
"""

import ctypes
import logging
import logging.handlers
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from env_loader import (
    executable_directory,
    find_env_file,
    is_frozen,
    load_environment,
    user_data_directory,
)

APP_NAME = "EcoTrack"
APP_DESCRIPTION = "Smart Waste Management System"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5000
DEFAULT_URL = f"http://{DEFAULT_HOST}:{DEFAULT_PORT}/"

HEALTH_PATH = "/health"
STARTUP_TIMEOUT_SECONDS = 12

LOG_FILE_NAME = "ecotrack.log"
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3


def setup_logging(log_dir: Path) -> logging.Logger:
    """Initialise file-based logging used before Flask logging takes over."""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / LOG_FILE_NAME

    logger = logging.getLogger("ecotrack.launcher")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s %(levelname)s [EcoTrack] %(message)s")

    file_handler = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.INFO)
    logger.addHandler(stream_handler)

    return logger


def show_error(title: str, message: str) -> None:
    """Show a Windows error dialog and log the message."""
    try:
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x0010)  # MB_ICONERROR
    except Exception:  # pragma: no cover - GUI not available
        pass


def port_is_occupied(host: str, port: int) -> bool:
    """Return True if something is already listening on host:port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def wait_for_server(health_url: str, timeout: float) -> bool:
    """Poll the /health endpoint until the server responds or timeout elapses."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urlopen(Request(health_url), timeout=1) as response:
                if response.status == 200:
                    return True
        except (URLError, HTTPError, OSError):
            time.sleep(0.25)
    return False


def check_database_connectivity(app) -> None:
    """Verify MySQL connectivity using the application's own engine.

    Raises RuntimeError with a user-facing message on failure.
    """
    from app.extensions import db
    from sqlalchemy import text

    with app.app_context():
        try:
            db.session.execute(text("SELECT 1"))
        except Exception as exc:  # pragma: no cover - runtime environment check
            raise RuntimeError(
                "Cannot connect to the MySQL database.\n\n"
                "Make sure MySQL 8 is running and that your .env file "
                "contains correct DB_HOST, DB_PORT, DB_USER, DB_PASSWORD "
                "and DB_NAME values.\n\n"
                "Original error: %s" % exc
            ) from exc


def main() -> int:
    exe_dir = executable_directory()
    user_data_dir = user_data_directory()
    log_dir = user_data_dir / "logs"
    upload_dir = user_data_dir / "uploads"

    logger = setup_logging(log_dir)
    logger.info("EcoTrack launcher starting (frozen=%s)", is_frozen())
    logger.info("Executable directory: %s", exe_dir)
    logger.info("User data directory: %s", user_data_dir)

    # Persistent writable locations are never inside the PyInstaller
    # temporary extraction directory.
    log_dir.mkdir(parents=True, exist_ok=True)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load environment configuration from an external .env file.
    #    Next to the executable, then %LOCALAPPDATA%\EcoTrack\.env.
    #    Process environment variables take precedence (override=False).
    env_path = load_environment()
    if env_path:
        logger.info("Loaded environment configuration from %s", env_path)
    else:
        logger.warning(
            "No .env file found next to the executable or in "
            "LOCALAPPDATA/EcoTrack",
        )

    # Application defaults, overridable via .env / system environment.
    os.environ.setdefault("FLASK_CONFIG", "default")
    os.environ.setdefault("FLASK_DEBUG", "0")
    os.environ.setdefault("UPLOAD_FOLDER", str(upload_dir))
    os.environ.setdefault("LOGGING_LEVEL", "INFO")

    # 2. Import and initialise the existing Flask application factory.
    try:
        from app import create_app
    except Exception as exc:  # pragma: no cover - packaging error
        logger.exception("Failed to import the Flask application factory")
        show_error(
            APP_NAME,
            "Failed to start EcoTrack: the application could not be loaded.\n\n"
            + str(exc),
        )
        return 1

    try:
        app = create_app()
    except Exception as exc:  # pragma: no cover - runtime error
        logger.exception("Failed to create the Flask application")
        show_error(
            APP_NAME,
            "Failed to initialise EcoTrack.\n\n" + str(exc),
        )
        return 1

    # 6. Flask debug mode and the development reloader stay disabled.
    app.config["DEBUG"] = False
    app.config["TESTING"] = False

    host = os.environ.get("ECO_TRACK_HOST", DEFAULT_HOST)
    try:
        port = int(os.environ.get("ECO_TRACK_PORT", str(DEFAULT_PORT)))
    except ValueError:
        port = DEFAULT_PORT

    # 8. Check whether the port is already occupied.
    if port_is_occupied(host, port):
        message = (
            f"Port {port} on {host} is already in use.\n\n"
            "EcoTrack cannot start. Another application (possibly another "
            "EcoTrack instance) is using this port. Close that application "
            "and try again."
        )
        logger.error("Port %s:%s is already occupied", host, port)
        show_error(APP_NAME, message)
        return 3

    # 9-10. Check MySQL connectivity before starting the server.
    try:
        check_database_connectivity(app)
    except RuntimeError as exc:
        logger.error("Database connectivity check failed: %s", exc)
        show_error(APP_NAME, str(exc))
        return 2

    # 11. Log the startup configuration (secrets are never logged).
    logger.info("Starting Waitress server on %s:%s", host, port)
    logger.info("Upload folder: %s", upload_dir)
    logger.info("Log folder: %s", log_dir)

    url = DEFAULT_URL

    # 7. Open the browser once Waitress is answering.
    def open_browser_when_ready() -> None:
        health_url = f"http://{host}:{port}{HEALTH_PATH}"
        if wait_for_server(health_url, STARTUP_TIMEOUT_SECONDS):
            logger.info("Application is ready; opening browser at %s", url)
            try:
                webbrowser.open(url)
            except Exception as exc:  # pragma: no cover - environment error
                logger.warning("Could not open the browser automatically: %s", exc)
        else:
            logger.warning(
                "Server did not respond to health checks in time; "
                "browser was not opened automatically."
            )

    threading.Thread(target=open_browser_when_ready, daemon=True).start()

    # 3-5. Serve with Waitress on 127.0.0.1:5000 (debug/reloader disabled).
    from waitress import serve

    try:
        serve(
            app,
            host=host,
            port=port,
            threads=4,
            url_scheme="http",
            ident="EcoTrack",
        )
    except KeyboardInterrupt:
        logger.info("Shutdown requested (Ctrl+C)")
    except Exception as exc:  # pragma: no cover - runtime error
        logger.exception("Waitress server stopped unexpectedly")
        show_error(
            APP_NAME,
            "EcoTrack server stopped unexpectedly:\n\n" + str(exc),
        )
        return 1
    finally:
        logger.info("EcoTrack stopped")

    return 0


if __name__ == "__main__":
    sys.exit(main())
