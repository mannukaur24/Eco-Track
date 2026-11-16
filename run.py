import sys

from app import create_app
from app.extensions import db
from sqlalchemy import text

app = create_app()


def _check_database() -> bool:
    """Verify MySQL connectivity before serving; print a clear diagnostic."""
    with app.app_context():
        try:
            db.session.execute(text("SELECT 1"))
        except Exception as exc:  # pragma: no cover - runtime environment check
            print("ERROR: Cannot connect to the MySQL database.", file=sys.stderr)
            print(
                "       Make sure MySQL 8 is running and your .env file contains "
                "correct DB_HOST, DB_PORT, DB_USER, DB_PASSWORD and DB_NAME values.",
                file=sys.stderr,
            )
            print("       Original error: %s" % exc, file=sys.stderr)
            return False
    return True


if __name__ == "__main__":
    if not _check_database():
        sys.exit(1)
    app.run()
