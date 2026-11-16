"""Tests for centralized environment loading, database configuration and the
connection diagnostic tool.

These tests run against SQLite / monkeypatched dependencies and never require a
live MySQL server. Real credentials are never asserted as literals or printed.
"""

import os
import socket
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import pymysql
from pymysql.err import OperationalError

# Make the tools directory importable so the diagnostic uses the same module
# as the application.
_TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import env_loader
import check_db_connection
from config import build_database_uri, _missing_db_vars  # noqa: E402
from app import create_app

PROJECT_ROOT = env_loader.source_project_root()


# ---------------------------------------------------------------------------
# env_loader: environment file discovery
# ---------------------------------------------------------------------------


def test_find_env_file_source_root(monkeypatch):
    """Source mode resolves EcoTrack/.env from __file__, not cwd."""
    monkeypatch.setattr(env_loader, "is_frozen", lambda: False)
    found = env_loader.find_env_file()
    assert found is not None
    assert found.name == ".env"
    assert found == PROJECT_ROOT / ".env"


def test_find_env_file_exe_adjacent_onedir(monkeypatch, tmp_path):
    """Frozen mode loads .env next to the executable."""
    exe_dir = tmp_path / "dist" / "EcoTrack"
    exe_dir.mkdir(parents=True)
    (exe_dir / "EcoTrack.exe").write_text("", encoding="utf-8")
    (exe_dir / ".env").write_text("DB_PASSWORD=dotenv-value\n", encoding="utf-8")

    monkeypatch.setattr(env_loader, "is_frozen", lambda: True)
    monkeypatch.setattr(sys, "executable", str(exe_dir / "EcoTrack.exe"))

    found = env_loader.find_env_file()
    assert found == exe_dir / ".env"


def test_find_env_file_onefile(monkeypatch, tmp_path):
    """Frozen onefile mode loads .env next to the EXE itself."""
    exe = tmp_path / "EcoTrack.exe"
    exe.write_text("", encoding="utf-8")
    (tmp_path / ".env").write_text("DB_PASSWORD=dotenv-value\n", encoding="utf-8")

    monkeypatch.setattr(env_loader, "is_frozen", lambda: True)
    monkeypatch.setattr(sys, "executable", str(exe))

    found = env_loader.find_env_file()
    assert found == tmp_path / ".env"


def test_find_env_file_localappdata_fallback(monkeypatch, tmp_path):
    """Frozen mode falls back to %LOCALAPPDATA%/EcoTrack/.env."""
    exe_dir = tmp_path / "dist" / "EcoTrack"
    exe_dir.mkdir(parents=True)
    (exe_dir / "EcoTrack.exe").write_text("", encoding="utf-8")
    # No .env next to the executable.

    local_app_data = tmp_path / "localappdata"
    (local_app_data / "EcoTrack").mkdir(parents=True)
    (local_app_data / "EcoTrack" / ".env").write_text(
        "DB_PASSWORD=localappdata-value\n", encoding="utf-8"
    )

    monkeypatch.setattr(env_loader, "is_frozen", lambda: True)
    monkeypatch.setattr(sys, "executable", str(exe_dir / "EcoTrack.exe"))
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))

    found = env_loader.find_env_file()
    assert found == local_app_data / "EcoTrack" / ".env"


def test_find_env_file_missing(monkeypatch, tmp_path):
    """Frozen mode with no .env anywhere returns None."""
    exe_dir = tmp_path / "dist" / "EcoTrack"
    exe_dir.mkdir(parents=True)
    (exe_dir / "EcoTrack.exe").write_text("", encoding="utf-8")
    local_app_data = tmp_path / "localappdata"
    (local_app_data / "EcoTrack").mkdir(parents=True)

    monkeypatch.setattr(env_loader, "is_frozen", lambda: True)
    monkeypatch.setattr(sys, "executable", str(exe_dir / "EcoTrack.exe"))
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))

    assert env_loader.find_env_file() is None


# ---------------------------------------------------------------------------
# env_loader: load_environment precedence
# ---------------------------------------------------------------------------


def test_load_environment_process_env_wins(monkeypatch, tmp_path):
    """Process environment variables take precedence over .env (override=False)."""
    dotenv_file = tmp_path / ".env"
    dotenv_file.write_text("DB_PASSWORD=dotenv-value\n", encoding="utf-8")

    monkeypatch.setenv("DB_PASSWORD", "process-value")
    loaded = env_loader.load_environment(dotenv_file, override=False)
    assert loaded == dotenv_file
    assert os.environ["DB_PASSWORD"] == "process-value"


def test_load_environment_override_true(monkeypatch, tmp_path):
    """override=True lets .env overwrite an existing process variable."""
    dotenv_file = tmp_path / ".env"
    dotenv_file.write_text("DB_PASSWORD=dotenv-value\n", encoding="utf-8")

    monkeypatch.setenv("DB_PASSWORD", "process-value")
    env_loader.load_environment(dotenv_file, override=True)
    assert os.environ["DB_PASSWORD"] == "dotenv-value"


def test_load_environment_missing_file_returns_none(tmp_path):
    assert env_loader.load_environment(tmp_path / "nonexistent.env") is None


# ---------------------------------------------------------------------------
# config: database URI construction
# ---------------------------------------------------------------------------


def _clear_db_env(monkeypatch):
    for name in ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD", "DATABASE_URL"):
        monkeypatch.delenv(name, raising=False)


def test_build_database_uri_all_present(monkeypatch):
    _clear_db_env(monkeypatch)
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "3306")
    monkeypatch.setenv("DB_NAME", "ecotrack")
    monkeypatch.setenv("DB_USER", "ecotrack_user")
    monkeypatch.setenv("DB_PASSWORD", "secret-value")

    uri = build_database_uri()
    assert uri is not None
    assert uri.drivername == "mysql+pymysql"
    assert uri.username == "ecotrack_user"
    assert uri.host == "localhost"
    assert uri.port == 3306
    assert uri.database == "ecotrack"
    assert uri.password == "secret-value"


def test_build_database_uri_special_char_password(monkeypatch):
    """Passwords with special characters are encoded by URL.create()."""
    _clear_db_env(monkeypatch)
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "3306")
    monkeypatch.setenv("DB_NAME", "ecotrack")
    monkeypatch.setenv("DB_USER", "ecotrack_user")
    monkeypatch.setenv("DB_PASSWORD", "p@ss:w%rd@x")

    uri = build_database_uri()
    assert uri is not None
    # The stored password round-trips exactly.
    assert uri.password == "p@ss:w%rd@x"
    # The rendered URL percent-encodes special characters (not raw concat).
    rendered = uri.render_as_string(hide_password=False)
    assert "%40" in rendered


def test_build_database_uri_database_url_precedence(monkeypatch):
    _clear_db_env(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", "mysql+pymysql://custom:pw@dbhost:3307/customdb")
    uri = build_database_uri()
    assert uri == "mysql+pymysql://custom:pw@dbhost:3307/customdb"


def test_build_database_uri_missing_password(monkeypatch):
    _clear_db_env(monkeypatch)
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "3306")
    monkeypatch.setenv("DB_NAME", "ecotrack")
    monkeypatch.setenv("DB_USER", "ecotrack_user")
    # DB_PASSWORD deliberately absent.
    assert build_database_uri() is None


def test_build_database_uri_missing_all(monkeypatch):
    _clear_db_env(monkeypatch)
    assert build_database_uri() is None


def test_build_database_uri_invalid_port(monkeypatch):
    _clear_db_env(monkeypatch)
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "not-a-port")
    monkeypatch.setenv("DB_NAME", "ecotrack")
    monkeypatch.setenv("DB_USER", "ecotrack_user")
    monkeypatch.setenv("DB_PASSWORD", "secret-value")
    assert build_database_uri() is None


# ---------------------------------------------------------------------------
# config: validation via create_app
# ---------------------------------------------------------------------------


def test_create_app_development_uses_root_env(monkeypatch):
    """Development app is created from the root .env configuration."""
    app = create_app("development")
    assert app is not None
    assert app.config["SQLALCHEMY_DATABASE_URI"] is not None


def test_create_app_testing_uses_sqlite(monkeypatch):
    """TestingConfig keeps SQLite; DB env vars are irrelevant."""
    app = create_app("testing")
    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///ecotrack_test.db"


def test_validate_database_configuration_reports_missing(monkeypatch):
    """Missing DB config raises a clear RuntimeError without revealing secrets."""
    from config import DevelopmentConfig, _missing_db_vars

    _clear_db_env(monkeypatch)
    app = create_app("testing")
    app.config["SQLALCHEMY_DATABASE_URI"] = None
    with pytest.raises(RuntimeError) as excinfo:
        DevelopmentConfig._validate_database_configuration(app)
    message = str(excinfo.value)
    assert "DB_PASSWORD" in message
    assert "secret" not in message.lower() and "3688" not in message


# ---------------------------------------------------------------------------
# check_db_connection: error classification
# ---------------------------------------------------------------------------


def test_error_kind_classification():
    assert check_db_connection._error_kind(OperationalError(1045, "x")) == "access denied"
    assert check_db_connection._error_kind(OperationalError(1049, "x")) == "unknown database"
    assert check_db_connection._error_kind(OperationalError(2003, "x")) == "server unavailable"
    assert check_db_connection._error_kind(OperationalError(9999, "x")) == "connection error"


def test_tcp_connectable(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect_ex", lambda self, addr: 0)
    assert check_db_connection.tcp_connectable("localhost", 3306) is True

    monkeypatch.setattr(socket.socket, "connect_ex", lambda self, addr: 1)
    assert check_db_connection.tcp_connectable("localhost", 3306) is False


def test_attempt_authentication_success(monkeypatch):
    mock_conn = MagicMock()
    monkeypatch.setattr(pymysql, "connect", lambda **kwargs: mock_conn)
    ok, kind, message = check_db_connection.attempt_authentication(
        "localhost", 3306, "user", "pass"
    )
    assert ok is True
    assert kind is None
    assert message == "Successful"


def test_attempt_authentication_access_denied(monkeypatch):
    def fail_connect(**kwargs):
        raise OperationalError(1045, "Access denied")

    monkeypatch.setattr(pymysql, "connect", fail_connect)
    ok, kind, message = check_db_connection.attempt_authentication(
        "localhost", 3306, "user", "pass"
    )
    assert ok is False
    assert kind == "access denied"


def test_attempt_authentication_server_unavailable(monkeypatch):
    def fail_connect(**kwargs):
        raise OperationalError(2003, "Can't connect")

    monkeypatch.setattr(pymysql, "connect", fail_connect)
    ok, kind, message = check_db_connection.attempt_authentication(
        "localhost", 3306, "user", "pass"
    )
    assert ok is False
    assert kind == "server unavailable"


def test_attempt_database_access_unknown_database(monkeypatch):
    def fail_connect(**kwargs):
        raise OperationalError(1049, "Unknown database")

    monkeypatch.setattr(pymysql, "connect", fail_connect)
    ok, kind, message = check_db_connection.attempt_database_access(
        "localhost", 3306, "user", "pass", "ecotrack"
    )
    assert ok is False
    assert kind == "unknown database"


# ---------------------------------------------------------------------------
# check_db_connection: masked diagnostics (no secret leakage)
# ---------------------------------------------------------------------------


def test_main_missing_environment_file(monkeypatch, capsys):
    monkeypatch.setattr(env_loader, "find_env_file", lambda: None)
    # load_environment uses find_env_file from env_loader module.
    code = check_db_connection.main()
    out = capsys.readouterr().out
    assert code == 1
    assert "not found" in out
    assert "MISSING ENVIRONMENT FILE" in out


def test_main_missing_configuration_values(monkeypatch, capsys):
    monkeypatch.setattr(
        check_db_connection,
        "load_configuration",
        lambda: (PROJECT_ROOT / ".env", {v: None for v in check_db_connection.REQUIRED_VARS} | {"SECRET_KEY": None}),
    )
    code = check_db_connection.main()
    out = capsys.readouterr().out
    assert code == 1
    assert "MISSING CONFIGURATION VALUES" in out


def test_main_ready_output_is_masked(monkeypatch, capsys):
    """Successful run reports READY and never prints the password or secret key."""
    # All required vars present (real .env supplies them).
    monkeypatch.setattr(socket.socket, "connect_ex", lambda self, addr: 0)

    mock_conn = MagicMock()
    monkeypatch.setattr(pymysql, "connect", lambda **kwargs: mock_conn)

    code = check_db_connection.main()
    out = capsys.readouterr().out

    assert code == 0
    assert "Result: READY" in out
    assert "DB_PASSWORD: configured (hidden)" in out
    assert "Environment file: detected" in out
    # Secrets must not appear in the output.
    secret = os.environ.get("DB_PASSWORD", "")
    assert secret and secret not in out
    secret_key = os.environ.get("SECRET_KEY")
    if secret_key:
        assert secret_key not in out


def test_main_access_denied(monkeypatch, capsys):
    monkeypatch.setattr(socket.socket, "connect_ex", lambda self, addr: 0)

    def fail_connect(**kwargs):
        raise OperationalError(1045, "Access denied for user")

    monkeypatch.setattr(pymysql, "connect", fail_connect)
    code = check_db_connection.main()
    out = capsys.readouterr().out
    assert code == 3
    assert "ACCESS DENIED" in out
    assert "Result: ACCESS DENIED" in out


def test_main_server_unavailable(monkeypatch, capsys):
    monkeypatch.setattr(socket.socket, "connect_ex", lambda self, addr: 1)
    code = check_db_connection.main()
    out = capsys.readouterr().out
    assert code == 2
    assert "SERVER UNAVAILABLE" in out
