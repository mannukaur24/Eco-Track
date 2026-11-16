"""Citizen portal tests: complaint submission, validation, ownership, history."""

import io
import pytest
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.waste_category import WasteCategory
from app.models.report import Report
from app.utils.uploads import validate_image, UploadError
from werkzeug.datastructures import FileStorage


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        cats = [
            "Organic Waste", "Plastic Waste", "Electronic Waste",
            "Household Waste", "Construction Waste", "Industrial Waste", "Other",
        ]
        for name in cats:
            if not WasteCategory.query.filter_by(category_name=name).first():
                db.session.add(WasteCategory(category_name=name))
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _register(client, email, full_name, password="Password123"):
    return client.post(
        "/auth/register",
        data={
            "full_name": full_name,
            "email": email,
            "password": password,
            "confirm_password": password,
            "role": "Citizen",
            "phone": "1234567890",
        },
        follow_redirects=True,
    )


def _login(client, email, password="Password123"):
    return client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )


def _make_image_file(name="test.png", content_type="image/png", size_kb=1):
    """Return a FileStorage wrapping a minimal valid PNG-like buffer."""
    # Minimal PNG header (8 bytes) + IEND chunk to be a detectable image
    png_header = b"\x89PNG\r\n\x1a\n"
    data = png_header + b"\x00" * (size_kb * 1024)
    return FileStorage(
        stream=io.BytesIO(data),
        filename=name,
        content_type=content_type,
    )


def _submit_complaint(client, image=None, **overrides):
    data = {
        "category_id": "1",
        "description": ("There is a large pile of garbage on the street corner "
                        "that has not been collected for weeks."),
        "address_text": "123 Main Street, City",
        "latitude": "28.6139",
        "longitude": "77.2090",
        "additional_info": "Near the bus stop.",
    }
    data.update(overrides)
    if image is not None:
        data["image"] = image
    return client.post(
        "/citizen/submit",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )


def test_submit_complaint_valid(client):
    _register(client, "citizen1@example.com", "Citizen One")
    _login(client, "citizen1@example.com")
    image = _make_image_file("photo.png")
    response = _submit_complaint(client, image=image)
    assert response.status_code == 200
    assert b"Complaint submitted successfully" in response.data
    user = User.query.filter_by(email="citizen1@example.com").first()
    report = Report.query.filter_by(user_id=user.id).first()
    assert report is not None
    assert report.reference is not None
    assert report.reference.startswith("ET-")
    assert report.status == "Pending"
    assert report.image_path is not None
    assert report.image_path.endswith(".png")


def test_submit_complaint_missing_category(client):
    _register(client, "c2@example.com", "Citizen Two")
    _login(client, "c2@example.com")
    response = _submit_complaint(client, category_id="")
    assert b"Please select a waste category" in response.data


def test_submit_complaint_short_description(client):
    _register(client, "c3@example.com", "Citizen Three")
    _login(client, "c3@example.com")
    response = _submit_complaint(client, description="Too short")
    assert b"at least 10 characters" in response.data


def test_submit_complaint_no_address(client):
    _register(client, "c4@example.com", "Citizen Four")
    _login(client, "c4@example.com")
    response = _submit_complaint(client, address_text="")
    assert b"Please provide an address" in response.data


def test_submit_complaint_invalid_image_format(client):
    _register(client, "c5@example.com", "Citizen Five")
    _login(client, "c5@example.com")
    bad_file = FileStorage(
        stream=io.BytesIO(b"this is not an image"),
        filename="document.txt",
        content_type="text/plain",
    )
    response = _submit_complaint(client, image=bad_file)
    assert b"Invalid image type" in response.data or b"not a valid image" in response.data


def test_validate_image_oversized():
    """Directly test the upload size validation."""
    big = io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * (6 * 1024 * 1024))
    # simulate a file that reports 6MB size

    class FakeStorage:
        filename = "big.png"

        def __init__(self, stream):
            self.stream = stream

        def seek(self, *a, **k):
            return self.stream.seek(*a, **k)

        def tell(self):
            return 6 * 1024 * 1024

        def read(self, *a, **k):
            return self.stream.read(*a, **k)

    fs = FakeStorage(big)
    with pytest.raises(UploadError) as excinfo:
        validate_image(fs)
    assert "5 MB" in str(excinfo.value)


def test_unique_references(client):
    _register(client, "c6@example.com", "Citizen Six")
    _login(client, "c6@example.com")
    _submit_complaint(client, image=_make_image_file("a.png"))
    _submit_complaint(
        client,
        image=_make_image_file("b.png"),
        description="Another pile of waste dumped near the park area, needs urgent removal.",
    )
    user = User.query.filter_by(email="c6@example.com").first()
    reports = Report.query.filter_by(user_id=user.id).all()
    references = [r.reference for r in reports]
    assert len(references) == len(set(references))
    assert all(r.startswith("ET-") for r in references)


def test_complaint_ownership(client):
    """Citizen A cannot view Citizen B's complaint."""
    _register(client, "owner@example.com", "Owner User")
    _login(client, "owner@example.com")
    _submit_complaint(client, image=_make_image_file("x.png"))
    owner = User.query.filter_by(email="owner@example.com").first()
    report = Report.query.filter_by(user_id=owner.id).first()

    # Register and login as a different citizen
    client.get("/auth/logout", follow_redirects=True)
    _register(client, "other@example.com", "Other User")
    _login(client, "other@example.com")

    # Try to access owner's report directly
    response = client.get(f"/citizen/complaint/{report.reference}", follow_redirects=True)
    assert b"not found or you do not have access" in response.data


def test_complaint_history(client):
    _register(client, "c7@example.com", "Citizen Seven")
    _login(client, "c7@example.com")
    _submit_complaint(client, image=_make_image_file("h.png"))
    response = client.get("/citizen/history", follow_redirects=True)
    assert response.status_code == 200
    assert b"ET-" in response.data


def test_citizen_dashboard(client):
    _register(client, "c8@example.com", "Citizen Eight")
    _login(client, "c8@example.com")
    response = client.get("/citizen/dashboard", follow_redirects=True)
    assert response.status_code == 200
    assert b"Citizen Dashboard" in response.data
