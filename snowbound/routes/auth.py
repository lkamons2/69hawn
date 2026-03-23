import smtplib
from email.mime.text import MIMEText
from flask import (
    Blueprint, render_template, request, session,
    redirect, url_for, flash, abort, current_app,
)
from datetime import datetime, timedelta
import secrets
from .. import db
from ..models import OwnerEmail, MagicLink, Owner

bp = Blueprint("auth", __name__)


def _send_magic_link_email(to_email, magic_url):
    """Send magic link via SMTP. Falls back to flash message if SMTP not configured."""
    host = current_app.config.get("SMTP_HOST", "")
    if not host:
        flash(f"Magic link (dev only — SMTP not configured): {magic_url}", "info")
        return

    port = current_app.config.get("SMTP_PORT", 587)
    user = current_app.config.get("SMTP_USER", "")
    password = current_app.config.get("SMTP_PASS", "")
    from_addr = current_app.config.get("SMTP_FROM", "info@69hawn.com")

    body = (
        f"Click the link below to log in to the Snowbound LLC Condo Calendar.\n\n"
        f"{magic_url}\n\n"
        f"This link expires in {current_app.config.get('MAGIC_LINK_EXPIRY_MINUTES', 15)} minutes "
        f"and can only be used once.\n\n"
        f"If you did not request this link, you can ignore this email."
    )

    msg = MIMEText(body)
    msg["Subject"] = "Snowbound LLC Calendar — Login Link"
    msg["From"] = from_addr
    msg["To"] = to_email

    try:
        with smtplib.SMTP(host, port) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(user, password)
            smtp.sendmail(from_addr, [to_email], msg.as_string())
        flash("Login link sent — check your email.", "info")
    except Exception as e:
        current_app.logger.error(f"SMTP error: {e}")
        flash(f"Could not send email. Magic link (dev fallback): {magic_url}", "error")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        owner_email = OwnerEmail.query.filter_by(email=email).first()
        if owner_email:
            token = secrets.token_urlsafe(32)
            expiry = datetime.utcnow() + timedelta(
                minutes=current_app.config["MAGIC_LINK_EXPIRY_MINUTES"]
            )
            link = MagicLink(email=email, token=token, expires_at=expiry)
            db.session.add(link)
            db.session.commit()
            magic_url = url_for("auth.verify", token=token, _external=True)
            _send_magic_link_email(email, magic_url)
        else:
            flash("Email not recognized.", "error")
        return redirect(url_for("auth.login"))
    return render_template("login.html")


@bp.route("/auth/<token>")
def verify(token):
    link = MagicLink.query.filter_by(token=token, used=False).first()
    if not link or link.expires_at < datetime.utcnow():
        abort(403)
    link.used = True
    db.session.commit()

    owner_email = OwnerEmail.query.filter_by(email=link.email).first()
    if not owner_email:
        abort(403)

    owner = Owner.query.get(owner_email.owner_id)
    session.permanent = True
    session["owner_id"] = owner.id
    session["owner_short_name"] = owner.short_name
    session["is_admin"] = owner.is_admin

    return redirect(url_for("calendar.current"))


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
