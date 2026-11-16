"""Configuration tests for EcoTrack.

Covers the production SECRET_KEY requirement: a strong secret must be
provided via environment variable and the application must fail safely
when required production configuration is missing.
"""

import pytest

from app import create_app


def test_production_requires_secret_key(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app("production")


def test_production_rejects_weak_secret_key(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "weak")
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app("production")


def test_production_accepts_strong_secret_key(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "this-is-a-strong-test-secret-key-12345")
    app = create_app("production")
    assert app is not None
    assert app.config["SECRET_KEY"] == "this-is-a-strong-test-secret-key-12345"


def test_development_works_without_secret_key(monkeypatch):
    """Local development stays convenient without a production secret."""
    monkeypatch.delenv("SECRET_KEY", raising=False)
    app = create_app("development")
    assert app is not None


def test_testing_config_has_test_secret_key():
    app = create_app("testing")
    assert app.config["SECRET_KEY"]
    assert app.config["SECRET_KEY"] != "dev-secret-key-change-me"
