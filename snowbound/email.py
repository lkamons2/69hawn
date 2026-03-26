import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app


def _smtp_send(to_addr, subject, body_text, body_html=None):
    """Low-level SMTP send to a single address. Returns True if sent."""
    host = current_app.config.get("SMTP_HOST", "")
    if not host:
        current_app.logger.info(
            "SMTP not configured — email not sent. Subject: %s", subject
        )
        return False

    from_addr = current_app.config.get("SMTP_FROM", "info@69hawn.com")
    port = current_app.config.get("SMTP_PORT", 587)
    user = current_app.config.get("SMTP_USER", "")
    password = current_app.config.get("SMTP_PASS", "")

    if body_html:
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(body_text, "plain"))
        msg.attach(MIMEText(body_html, "html"))
    else:
        msg = MIMEText(body_text)

    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr

    try:
        with smtplib.SMTP(host, port) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(user, password)
            smtp.sendmail(from_addr, [to_addr], msg.as_string())
        current_app.logger.info("Email sent. Subject: %s | To: %s", subject, to_addr)
        return True
    except Exception as e:
        current_app.logger.error("SMTP error: %s", e)
        return False


def _testing_banner(real_recipients):
    """Build testing override banner text and html."""
    addr_list = ", ".join(real_recipients)
    text = (
        "*** TESTING OVERRIDE ***\n"
        f"This email would have been sent to: {addr_list}\n"
        "*** TESTING OVERRIDE ***\n\n"
    )
    html = (
        '<div style="background:#fff3cd;border:2px solid #ffc107;padding:10px;margin-bottom:15px;">'
        "<strong>*** TESTING OVERRIDE ***</strong><br>"
        f"This email would have been sent to: {addr_list}<br>"
        "<strong>*** TESTING OVERRIDE ***</strong>"
        "</div>"
    )
    return text, html


def send_email(to_emails, subject, body_text, body_html=None):
    """Send an email to a list of addresses.

    If TEST_EMAIL_OVERRIDE is set, the email is redirected to the override
    address with a banner showing who it would have gone to.

    Returns True if sent, False otherwise.
    """
    override = current_app.config.get("TEST_EMAIL_OVERRIDE", "")
    recipients = [e for e in to_emails if e]
    if not recipients:
        return False

    if override:
        banner_text, banner_html = _testing_banner(recipients)
        override_subject = f"[TEST] {subject}"
        override_text = banner_text + body_text
        override_html = None
        if body_html:
            override_html = banner_html + body_html
        return _smtp_send(override, override_subject, override_text, override_html)
    else:
        return _smtp_send(", ".join(recipients), subject, body_text, body_html)


def send_trade_notification(owner_email_map, subject, body_text, body_html=None):
    """Send trade notification emails — one per owner.

    owner_email_map: list of (owner_name, [email1, email2, ...]) tuples.

    If TEST_EMAIL_OVERRIDE is set, sends one email per owner to the override
    address, each clearly indicating who it would have gone to.

    Also sends an admin CC copy.

    Returns True if any email was sent successfully.
    """
    override = current_app.config.get("TEST_EMAIL_OVERRIDE", "")
    admin_email = current_app.config.get("ADMIN_EMAIL", "")
    any_sent = False

    for owner_name, emails in owner_email_map:
        real_recipients = [e for e in emails if e]
        if not real_recipients:
            continue

        if override:
            banner_text, banner_html = _testing_banner(real_recipients)
            owner_subject = f"[TEST] {subject}"
            owner_text = banner_text + body_text
            owner_html = None
            if body_html:
                owner_html = banner_html + body_html
            if _smtp_send(override, owner_subject, owner_text, owner_html):
                any_sent = True
        else:
            addr = ", ".join(real_recipients)
            if _smtp_send(addr, subject, body_text, body_html):
                any_sent = True

    # Admin CC copy
    if admin_email:
        if override:
            banner_text, banner_html = _testing_banner([admin_email])
            admin_subject = f"[TEST] Admin: {subject}"
            admin_text = banner_text + body_text
            admin_html = None
            if body_html:
                admin_html = banner_html + body_html
            _smtp_send(override, admin_subject, admin_text, admin_html)
        else:
            admin_subject = f"Admin: {subject}"
            _smtp_send(admin_email, admin_subject, body_text, body_html)

    return any_sent


def get_owner_emails(owner):
    """Collect all email addresses for an owner."""
    return [c.email for c in owner.contacts if c.email]
