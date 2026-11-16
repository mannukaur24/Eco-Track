"""EcoTrack database connection diagnostic.

Loads configuration using the same centralized loader used by Flask
(`env_loader.load_environment`) and reports the state of the MySQL connection
without ever printing `DB_PASSWORD` or `SECRET_KEY`.

Run from the project root:

    python tools/check_db_connection.py

Exit codes:
    0 - READY (server reachable, authentication and database access OK)
    1 - Missing environment file or missing configuration values
    2 - MySQL server unavailable
    3 - Access denied (invalid credentials)
    4 - Unknown database
"""

import os
import socket
import sys
from pathlib import Path

# Allow running as `python tools/check_db_connection.py` from the project root.
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pymysql
from pymysql.err import OperationalError

from env_loader import find_env_file, load_environment, user_data_directory

REQUIRED_VARS = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD")

# MySQL error codes.
CR_SERVER_GONE = 2003
ER_ACCESS_DENIED = 1045
ER_BAD_DB = 1049


def _var_source(name: str) -> str:
    """Where a configuration value currently comes from."""
    if name in os.environ:
        return "process environment"
    return "not set"


def _masked(value: str | None) -> str:
    return "configured (hidden)" if value else "missing"


def load_configuration():
    """Load environment and return (env_path, values dict)."""
    env_path = load_environment()
    values = {name: os.environ.get(name) for name in REQUIRED_VARS}
    values["SECRET_KEY"] = os.environ.get("SECRET_KEY")
    return env_path, values


def tcp_connectable(host: str, port: int, timeout: float = 3.0) -> bool:
    """Return True if a TCP connection to host:port succeeds."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((host, port)) == 0


def _error_kind(exc: OperationalError) -> str:
    code = exc.args[0] if exc.args else None
    if code == ER_ACCESS_DENIED:
        return "access denied"
    if code == ER_BAD_DB:
        return "unknown database"
    if code in (CR_SERVER_GONE, 2002, 2013):
        return "server unavailable"
    return "connection error"


def attempt_authentication(host, port, user, password):
    """Authenticate to the MySQL server without selecting a database.

    Returns (ok, kind, message).
    """
    try:
        conn = pymysql.connect(
            host=host, port=port, user=user, password=password, connect_timeout=5
        )
        conn.close()
        return True, None, "Successful"
    except OperationalError as exc:
        return False, _error_kind(exc), str(exc)
    except Exception as exc:  # pragma: no cover - depends on environment
        return False, "server unavailable", str(exc)


def attempt_database_access(host, port, user, password, database):
    """Attempt to connect to a specific database.

    Returns (ok, kind, message).
    """
    try:
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            connect_timeout=5,
        )
        conn.close()
        return True, None, "Successful"
    except OperationalError as exc:
        return False, _error_kind(exc), str(exc)
    except Exception as exc:  # pragma: no cover - depends on environment
        return False, "server unavailable", str(exc)


def main() -> int:
    env_path, values = load_configuration()

    host = values["DB_HOST"]
    port_raw = values["DB_PORT"]
    name = values["DB_NAME"]
    user = values["DB_USER"]
    password = values["DB_PASSWORD"]

    print("EcoTrack Database Diagnostics")
    if env_path:
        print("Environment file: detected (%s)" % env_path)
    else:
        print("Environment file: not found")

    print("DB_HOST: %s" % (host or "missing"))
    print("DB_PORT: %s" % (port_raw or "missing"))
    print("DB_NAME: %s" % (name or "missing"))
    print("DB_USER: %s" % (user or "missing"))
    print("DB_PASSWORD: %s" % _masked(password))

    # Configuration-level checks.
    missing = [v for v in REQUIRED_VARS if not values[v]]
    if env_path is None:
        print("\nResult: MISSING ENVIRONMENT FILE")
        print("        Create .env next to the executable (or at %s/EcoTrack/.env)"
              % user_data_directory())
        return 1
    if missing:
        print("\nResult: MISSING CONFIGURATION VALUES")
        print("        Missing: " + ", ".join(missing))
        return 1

    try:
        port = int(port_raw)
    except (TypeError, ValueError):
        print("\nResult: INVALID CONFIGURATION")
        print("        DB_PORT must be an integer (got %r)" % port_raw)
        return 1

    # TCP connectivity.
    print("\nMYSQL SERVER: ", end="")
    if not tcp_connectable(host, port):
        print("Unavailable (could not reach %s:%s)" % (host, port))
        print("\nResult: SERVER UNAVAILABLE")
        return 2
    print("Connected")

    # Authentication.
    print("AUTHENTICATION: ", end="")
    ok, kind, message = attempt_authentication(host, port, user, password)
    if not ok:
        print("Failed (%s)" % kind)
        print("\nResult: ACCESS DENIED" if kind == "access denied" else "\nResult: CONNECTION FAILED")
        print("        %s" % message)
        return 3 if kind == "access denied" else 2

    print("Successful")

    # Database access.
    print("DATABASE ACCESS: ", end="")
    ok, kind, message = attempt_database_access(host, port, user, password, name)
    if not ok:
        print("Failed (%s)" % kind)
        if kind == "unknown database":
            print("\nResult: UNKNOWN DATABASE")
            return 4
        print("\nResult: DATABASE ACCESS FAILED")
        print("        %s" % message)
        return 2

    print("Successful")

    print("\nResult: READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
