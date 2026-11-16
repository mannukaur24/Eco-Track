"""Centralized environment configuration loading for EcoTrack.

This module is the single place where the application discovers and loads its
external `.env` file. It is used by `config.py` (Flask configuration),
`desktop_launcher.py` (packaged executable) and `tools/check_db_connection.py`
(diagnostic tool) so that source, onedir and onefile builds all resolve the
same configuration deterministically.

Environment file discovery
--------------------------
Source / development (not frozen):
    EcoTrack/.env
    Resolved from this file's actual path (__file__), NOT from the terminal's
    current working directory, so `flask db upgrade`, `python run.py` etc.
    work from any working directory.

Packaged ONEDIR (dist/EcoTrack/EcoTrack.exe):
    .env adjacent to the executable, then %LOCALAPPDATA%\\EcoTrack\\.env.

Packaged ONEFILE (dist/EcoTrack.exe):
    .env adjacent to the executable, then %LOCALAPPDATA%\\EcoTrack\\.env.

PyInstaller's temporary extraction directory (_MEIPASS) is never used for
configuration; writable data always lives outside the bundle.

Precedence (deterministic, documented)
--------------------------------------
When the same variable exists in more than one source, the winner is:

    1. Process environment variables  (highest priority - always win)
    2. Values from the discovered .env file
    3. Hard-coded defaults in config.py (lowest priority)

`load_dotenv` is always invoked with `override=False`, so an existing process
environment variable is never overwritten by a `.env` value. The `.env` file
supplies defaults only. A real `.env` is never bundled into the executable.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

APP_NAME = "EcoTrack"


def is_frozen() -> bool:
    """True when running from a PyInstaller bundle."""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def source_project_root() -> Path:
    """Resolve the source project root from this file's actual path.

    Does not depend on the terminal's current working directory.
    """
    return Path(__file__).resolve().parent


def user_data_directory() -> Path:
    """Persistent per-user application data directory (%LOCALAPPDATA%\\EcoTrack)."""
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / APP_NAME


def executable_directory() -> Path:
    """Directory containing the executable (onedir) or the EXE itself (onefile)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def find_env_file() -> Path | None:
    """Locate the external .env file.

    Returns the path of the first existing candidate, or None.
    """
    if is_frozen():
        # Packaged: look next to the executable, then in the user data dir.
        candidates = [executable_directory() / ".env", user_data_directory() / ".env"]
    else:
        # Source: the root .env resolved from __file__, not cwd.
        candidates = [source_project_root() / ".env"]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def load_environment(env_file: Path | None = None, override: bool = False) -> Path | None:
    """Load environment variables from an .env file.

    Returns the path of the file that was loaded, or None when no file was
    found.

    By default (override=False) process environment variables take precedence
    over .env values; the .env file supplies defaults only. Pass
    override=True to let .env values overwrite existing process variables.
    """
    if env_file is None:
        env_file = find_env_file()
    if env_file is not None and env_file.is_file():
        load_dotenv(dotenv_path=str(env_file), override=override)
        return env_file
    return None
