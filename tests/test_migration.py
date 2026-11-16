"""Database migration tests for EcoTrack.

Verifies that the committed initial migration can initialize a fresh
database from all SQLAlchemy models without destructive operations.
"""

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import text

from app import create_app
from app.extensions import db


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.drop_all()
        yield app
        db.session.remove()
        db.drop_all()


def _alembic_config(app):
    with app.app_context():
        engine = db.engine
        cfg = AlembicConfig("migrations/alembic.ini")
        cfg.set_main_option("script_location", "migrations")
        database_url = engine.url.render_as_string(hide_password=False)
        cfg.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
        return cfg


def test_initial_migration_upgrades_fresh_database(app):
    with app.app_context():
        # alembic_version is not part of SQLAlchemy metadata, so db.drop_all()
        # does not remove it; clear it so the upgrade runs against a fresh DB.
        db.session.execute(text("DROP TABLE IF EXISTS alembic_version"))
        db.session.commit()
        cfg = _alembic_config(app)
        command.upgrade(cfg, "head")

        from sqlalchemy import inspect

        inspector = inspect(db.engine)
        tables = set(inspector.get_table_names())

        expected = {
            "users",
            "staff",
            "waste_categories",
            "locations",
            "reports",
            "collection_tasks",
            "report_status_history",
            "task_updates",
            "awareness_articles",
        }
        missing = expected - tables
        assert not missing, f"Missing tables after migration: {sorted(missing)}"


def test_initial_migration_has_down_revision_none():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "initial_migration", "migrations/versions/1f8c95333bc2_initial_schema.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.down_revision is None
    assert callable(module.upgrade)
    assert callable(module.downgrade)
