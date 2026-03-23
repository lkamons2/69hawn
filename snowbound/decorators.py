from functools import wraps
from flask import session, redirect, url_for, abort


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("owner_id"):
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("owner_id"):
            return redirect(url_for("auth.login"))
        if not session.get("is_admin"):
            abort(403)
        return f(*args, **kwargs)
    return decorated
