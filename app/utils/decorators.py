from functools import wraps
from flask import abort, redirect, url_for, request, flash
from flask_login import current_user
from app.models.user import Role


def roles_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login", next=request.path))
            if current_user.role not in roles:
                flash("You do not have permission to access this page.", "danger")
                return abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def citizen_required(f):
    return roles_required(Role.CITIZEN)(f)


def administrator_required(f):
    return roles_required(Role.ADMINISTRATOR)(f)


def staff_required(f):
    return roles_required(Role.STAFF)(f)


def admin_or_staff_required(f):
    return roles_required(Role.ADMINISTRATOR, Role.STAFF)(f)
