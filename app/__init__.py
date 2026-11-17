import logging
import os
from flask import Flask, render_template
from config import config
from app.extensions import db, migrate, login_manager, csrf


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get("FLASK_CONFIG", "default")

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Logging
    _configure_logging(app)

    # User loader
    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.citizen import citizen_bp
    from app.routes.admin import admin_bp
    from app.routes.staff import staff_bp
    from app.routes.admin_analytics import analytics_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(citizen_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(staff_bp)
    app.register_blueprint(analytics_bp)

    # Error handlers
    _register_error_handlers(app)

    # Global template context
    _register_template_context(app)

    # CLI commands
    _register_cli_commands(app)

    app.logger.info("EcoTrack application created (config=%s)", config_name)
    return app


def _configure_logging(app):
    level = getattr(logging, app.config.get("LOGGING_LEVEL", "INFO"), logging.INFO)
    handler = logging.StreamHandler()
    handler.setLevel(level)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    app.logger.setLevel(level)
    app.logger.propagate = False


def _register_error_handlers(app):
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        app.logger.exception("Server error: %s", e)
        return render_template("errors/500.html"), 500


def _register_template_context(app):
    from app.models.user import Role, ReportStatus, TaskStatus

    @app.context_processor
    def inject_globals():
        return dict(
            app_name="EcoTrack",
            Role=Role,
            ReportStatus=ReportStatus,
            TaskStatus=TaskStatus,
        )


def _register_cli_commands(app):
    from app.services.commands import seed_db, seed_categories, create_admin

    app.cli.add_command(seed_db)
    app.cli.add_command(seed_categories)
    app.cli.add_command(create_admin)
