import pytest
from app import create_app
from app.extensions import db
from app.models.user import User, Role
from app.models.waste_category import WasteCategory


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        # Seed waste categories
        categories = [
            "Organic Waste",
            "Plastic Waste",
            "Paper Waste",
            "Glass Waste",
            "Metal Waste",
            "E-Waste",
            "Hazardous Waste",
            "General Waste",
        ]
        for name in categories:
            if not WasteCategory.query.filter_by(category_name=name).first():
                db.session.add(WasteCategory(category_name=name))
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


@pytest.fixture
def citizen(client):
    client.post(
        "/auth/register",
        data={
            "full_name": "Citizen User",
            "email": "citizen@example.com",
            "password": "Password123",
            "confirm_password": "Password123",
            "role": "Citizen",
            "phone": "1234567890",
        },
        follow_redirects=True,
    )
    return User.query.filter_by(email="citizen@example.com").first()


@pytest.fixture
def staff_user(client):
    client.post(
        "/auth/register",
        data={
            "full_name": "Staff User",
            "email": "staff@example.com",
            "password": "Password123",
            "confirm_password": "Password123",
            "role": "Staff",
            "phone": "1234567891",
        },
        follow_redirects=True,
    )
    return User.query.filter_by(email="staff@example.com").first()


@pytest.fixture
def admin_user(app):
    with app.app_context():
        admin = User(
            full_name="Admin User",
            email="admin@example.com",
            role=Role.ADMINISTRATOR,
            phone="1234567892",
        )
        admin.set_password("AdminPass123")
        db.session.add(admin)
        db.session.commit()
        return admin
