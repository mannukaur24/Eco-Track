"""Consistent UTC datetime handling for EcoTrack.

Database DateTime columns are timezone-naive. All timestamps are generated as
timezone-naive UTC values so stored values and comparisons are always
consistent (no offset-naive vs offset-aware comparison errors).
"""

from datetime import datetime, timezone


def utc_now():
    """Return the current UTC time as a timezone-naive datetime.

    Safe for storage in timezone-naive DateTime columns and for comparison
    against values read back from the database.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
