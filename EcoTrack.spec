# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller specification for EcoTrack - Smart Waste Management System.

Build modes (run from the project root with the virtual environment activated):

    # ONEDIR (primary development and verification target)
    #   dist/EcoTrack/EcoTrack.exe  + supporting files
    pyinstaller EcoTrack.spec

    # ONEFILE (convenience deliverable)
    #   dist/EcoTrack.exe  (single-file executable)
    $env:ECO_TRACK_ONEFILE="1"      # PowerShell
    set ECO_TRACK_ONEFILE=1         # cmd.exe
    pyinstaller EcoTrack.spec

The spec is the single source of truth for PyInstaller configuration;
no manual hidden-import command-line arguments are required.
"""

import os

from PyInstaller.building.build_main import Analysis, COLLECT, EXE, PYZ
from PyInstaller.utils.hooks import collect_submodules, collect_dynamic_libs

ONEFILE = os.environ.get("ECO_TRACK_ONEFILE", "") == "1"

block_cipher = None

# ---------------------------------------------------------------------------
# Binaries: native extensions / shared libraries collected explicitly below
# (cryptography's Rust binding, plus any platform shared libraries).
# ---------------------------------------------------------------------------
binaries = []

# ---------------------------------------------------------------------------
# cryptography (RSA auth for MySQL caching_sha2_password / sha256_password).
# PyMySQL[rsa] imports cryptography.hazmat.* at runtime. PyInstaller's static
# scan does not discover these lazily-loaded hazmat modules or the native
# binding, so collect them explicitly:
#   * collect_submodules("cryptography")  -> every cryptography submodule
#                                             (primitives, bindings, backends,
#                                             ...), including the native
#                                             _rust.pyd extension module.
#   * collect_dynamic_libs("cryptography") -> any shared libraries (none for
#                                             the Rust build, kept for parity
#                                             with OpenSSL-wheel builds).
# No mysql_native_password fallback is used; MySQL 8 caching_sha2_password is
# preserved.
# ---------------------------------------------------------------------------
_crypto_submodules = collect_submodules("cryptography")
_crypto_binaries = collect_dynamic_libs("cryptography")

binaries += _crypto_binaries

# ---------------------------------------------------------------------------
# Application entry point: the desktop launcher, which imports and uses the
# existing create_app() factory from app/__init__.py (no duplicate app).
# ---------------------------------------------------------------------------
entry_point = ["desktop_launcher.py"]

# ---------------------------------------------------------------------------
# Data files bundled next to the code inside the package.
#
#   app/templates  - Jinja2 templates (Flask resolves them relative to the
#                    application root_path, i.e. the bundled app package).
#   app/static     - public CSS, JavaScript and images.
#   migrations     - Flask-Migrate / Alembic migration scripts (committed
#                    schema; bundled for completeness, not applied at runtime).
#   alembic.ini    - Alembic logging/configuration file.
#
# Writable runtime data (logs, uploads, local .env) is deliberately NOT
# bundled; the launcher creates it under %LOCALAPPDATA%\EcoTrack\.
# ---------------------------------------------------------------------------
datas = [
    ("app/templates", "app/templates"),
    ("app/static", "app/static"),
    # migrations/ (contains env.py, versions/, script.py.mako, README and
    # alembic.ini) is copied as a tree.
    ("migrations", "migrations"),
]

# ---------------------------------------------------------------------------
# Hidden imports: modules PyInstaller's dependency scan cannot find
# statically (Flask blueprints imported lazily inside create_app(),
# SQLAlchemy dialects, waitress internals, Alembic env module, dotenv).
# ---------------------------------------------------------------------------
hiddenimports = [
    # Application modules (factory imports blueprints/services lazily).
    "config",
    "env_loader",
    "app",
    "app.extensions",
    "app.models",
    "app.models.user",
    "app.models.report",
    "app.models.report_status_history",
    "app.models.location",
    "app.models.waste_category",
    "app.models.staff",
    "app.models.collection_task",
    "app.models.task_update",
    "app.models.awareness_article",
    "app.routes",
    "app.routes.main",
    "app.routes.auth",
    "app.routes.citizen",
    "app.routes.admin",
    "app.routes.staff",
    "app.routes.admin_analytics",
    "app.services",
    "app.services.commands",
    "app.services.complaint_service",
    "app.services.admin_service",
    "app.services.staff_service",
    "app.services.reports_service",
    "app.services.analytics_service",
    "app.utils",
    "app.utils.uploads",
    "app.utils.decorators",
    "app.utils.datetime",
    # Flask ecosystem.
    "flask",
    "flask.cli",
    "flask.signals",
    "flask_login",
    "flask_sqlalchemy",
    "flask_migrate",
    "flask_wtf",
    "flask_wtf.csrf",
    "wtforms",
    "wtforms.fields",
    "wtforms.validators",
    "email_validator",
    "dotenv",
    # Database drivers / dialects.
    "pymysql",
    "sqlalchemy",
    "sqlalchemy.dialects.mysql",
    "sqlalchemy.dialects.mysql.pymysql",
    # Migration tooling.
    "alembic",
    "alembic.script",
    "alembic.util",
    # Production WSGI server.
    "waitress",
    "waitress.utilities",
    # Flask dependencies.
    "blinker",
    "click",
    "werkzeug",
    "itsdangerous",
    "jinja2",
    "markupsafe",
    # cryptography (PyMySQL[rsa] MySQL caching_sha2_password / sha256_password
    # auth). Collect every cryptography submodule plus the native binding so
    # the _rust.pyd extension and hazmat primitives are bundled for both
    # ONEDIR and ONEFILE builds. mysql_native_password is not used.
    "cryptography",
    "cryptography.hazmat.backends",
    "cryptography.hazmat.bindings.openssl.binding",
] + _crypto_submodules

a = Analysis(
    entry_point,
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

exe_kwargs = dict(
    name="EcoTrack",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI application: errors go to the persistent log file
    icon="assets/EcoTrack.ico",
    version="assets/EcoTrack_version_info.txt",
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if ONEFILE:
    # dist/EcoTrack.exe  (single-file convenience deliverable)
    EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        **exe_kwargs,
    )
else:
    # dist/EcoTrack/EcoTrack.exe  (ONEDIR - primary target)
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        **exe_kwargs,
    )
    COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="EcoTrack",
    )
