import urllib.parse
from flask import Blueprint, render_template
from ..decorators import login_required
from ..models import Owner, OwnerEmail

bp = Blueprint("email_compose", __name__)


@bp.route("/email")
@login_required
def email():
    owners = Owner.query.filter_by(is_active=True).order_by(Owner.id).all()
    all_emails = []
    for owner in owners:
        for e in owner.emails:
            all_emails.append(e.email)

    emails_csv = ",".join(all_emails)
    emails_semi = ";".join(all_emails)

    gmail_url = (
        "https://mail.google.com/mail/?view=cm&fs=1&bcc="
        + urllib.parse.quote(emails_csv, safe="")
    )
    outlook_web_url = (
        "https://outlook.live.com/mail/0/deeplink/compose?bcc="
        + urllib.parse.quote(emails_semi, safe="")
    )
    mailto_url = "mailto:?bcc=" + urllib.parse.quote(emails_csv, safe="@,")

    return render_template(
        "email.html",
        gmail_url=gmail_url,
        outlook_web_url=outlook_web_url,
        mailto_url=mailto_url,
        all_emails=all_emails,
        emails_semi=emails_semi,
    )
