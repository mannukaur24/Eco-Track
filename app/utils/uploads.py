"""Secure file-upload helpers for EcoTrack.

Validates image extension, detected MIME content type (via magic bytes) and file size.
Generates safe, random server-side filenames and prevents path traversal.
"""

import os
import secrets
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

# Image magic-byte signatures (file header bytes -> extension)
IMAGE_MAGIC = {
    b"\x89PNG\r\n\x1a\n": "png",
    b"\xFF\xD8\xFF": "jpeg",
    b"GIF87a": "gif",
    b"GIF89a": "gif",
    b"RIFF": "webp",  # WEBP files start with RIFF....WEBP
}


class UploadError(Exception):
    """Raised when an uploaded file fails validation."""


def allowed_file(filename):
    """Return True if the filename has an allowed image extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _detect_image_type(header):
    """Detect image type from file header magic bytes."""
    for magic, ext in IMAGE_MAGIC.items():
        if header.startswith(magic):
            if ext == "webp":
                # WEBP: RIFF + size + WEBP
                if len(header) >= 12 and header[8:12] == b"WEBP":
                    return "webp"
                continue
            return ext
    return None


def validate_image(file_storage, max_size=MAX_FILE_SIZE):
    """Validate an uploaded image file.

    Checks extension, detected content type (via file magic bytes) and size.
    Returns the original filename and validated file storage on success.
    Raises UploadError with a clear message on failure.
    """
    if file_storage is None or file_storage.filename == "":
        raise UploadError("No file selected.")

    original_filename = file_storage.filename
    if not allowed_file(original_filename):
        raise UploadError(
            "Invalid image type. Allowed formats: PNG, JPG, JPEG, GIF, WEBP."
        )

    # Read file content to check size and detected type
    file_storage.stream.seek(0, os.SEEK_END)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)

    if size == 0:
        raise UploadError("The uploaded file is empty.")
    if size > max_size:
        max_mb = max_size // (1024 * 1024)
        raise UploadError(f"File too large. Maximum size is {max_mb} MB.")

    # Detect actual content type from file magic bytes
    header = file_storage.stream.read(32)
    file_storage.stream.seek(0)
    detected = _detect_image_type(header)
    if detected is None:
        raise UploadError("The file content is not a valid image.")

    return original_filename


def generate_safe_filename(original_filename):
    """Generate a server-generated, safe random filename preserving extension."""
    ext = original_filename.rsplit(".", 1)[1].lower()
    random_token = secrets.token_hex(16)
    safe_name = f"{random_token}.{ext}"
    return secure_filename(safe_name)


def save_uploaded_file(file_storage, upload_folder):
    """Save an uploaded file to the upload folder with a safe name.

    Returns the relative path stored in the database.
    Raises UploadError if the file cannot be saved.
    """
    os.makedirs(upload_folder, exist_ok=True)
    original_filename = validate_image(file_storage)
    safe_name = generate_safe_filename(original_filename)

    # Prevent path traversal: safe_name contains only alnum + dot
    dest_path = os.path.join(upload_folder, safe_name)
    dest_path = os.path.abspath(dest_path)
    upload_folder_abs = os.path.abspath(upload_folder)
    if not dest_path.startswith(upload_folder_abs + os.sep) and dest_path != upload_folder_abs:
        raise UploadError("Unsafe file path detected.")

    file_storage.save(dest_path)
    return os.path.join("uploads", safe_name).replace(os.sep, "/")
