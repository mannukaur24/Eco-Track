"""Complaint (waste report) business logic for EcoTrack."""

import uuid
from app.extensions import db
from app.models.report import Report
from app.models.location import Location
from app.models.waste_category import WasteCategory
from app.utils.uploads import save_uploaded_file


class ComplaintService:
    """Service layer for citizen waste-report operations."""

    @staticmethod
    def create_report(user, form_data, image_file, upload_folder):
        """Create a new waste report for a citizen.

        Args:
            user: The authenticated Citizen User.
            form_data: dict with category_id, description, address_text,
                       latitude, longitude, additional_info.
            image_file: Werkzeug FileStorage or None.
            upload_folder: filesystem path for uploads.

        Returns:
            The created Report instance.

        Raises:
            ValueError: if validation fails.
            UploadError: if image upload fails.
        """
        category_id = form_data.get("category_id")
        description = form_data.get("description", "").strip()
        address_text = form_data.get("address_text", "").strip()
        latitude = form_data.get("latitude")
        longitude = form_data.get("longitude")

        # Validate required fields
        if not category_id:
            raise ValueError("Please select a waste category.")
        if not description:
            raise ValueError("Please provide a complaint description.")
        if len(description) < 10:
            raise ValueError("Description must be at least 10 characters.")
        if len(description) > 2000:
            raise ValueError("Description must not exceed 2000 characters.")
        if not address_text:
            raise ValueError("Please provide an address.")

        # Validate category exists
        category = db.session.get(WasteCategory, int(category_id))
        if category is None:
            raise ValueError("Invalid waste category selected.")

        # Handle image upload
        image_path = None
        if image_file is not None and image_file.filename != "":
            image_path = save_uploaded_file(image_file, upload_folder)

        # Create or reuse location
        location = Location(
            address_text=address_text,
            latitude=float(latitude) if latitude not in (None, "") else None,
            longitude=float(longitude) if longitude not in (None, "") else None,
        )
        db.session.add(location)
        db.session.flush()

        # Generate unique reference
        reference = "ET-" + uuid.uuid4().hex[:8].upper()
        while Report.query.filter_by(reference=reference).first():
            reference = "ET-" + uuid.uuid4().hex[:8].upper()

        report = Report(
            user_id=user.id,
            category_id=category.id,
            location_id=location.id,
            description=description,
            image_path=image_path,
            status="Pending",
            reference=reference,
        )
        db.session.add(report)
        db.session.commit()
        return report

    @staticmethod
    def get_user_reports(user, status_filter=None, search=None):
        """Return reports belonging to a user, optionally filtered."""
        query = Report.query.filter_by(user_id=user.id)
        if status_filter:
            query = query.filter_by(status=status_filter)
        if search:
            query = query.filter(Report.reference.ilike(f"%{search}%"))
        return query.order_by(Report.created_at.desc()).all()

    @staticmethod
    def get_report_by_reference(reference, user):
        """Return a report by reference if it belongs to the user."""
        return Report.query.filter_by(reference=reference, user_id=user.id).first()

    @staticmethod
    def dashboard_stats(user):
        """Return complaint statistics for a citizen dashboard."""
        reports = Report.query.filter_by(user_id=user.id).all()
        return {
            "total": len(reports),
            "pending": sum(1 for r in reports if r.status == "Pending"),
            "under_review": sum(1 for r in reports if r.status == "Verified"),
            "resolved": sum(1 for r in reports if r.status == "Completed"),
            "rejected": sum(1 for r in reports if r.status == "Rejected"),
        }
