import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///snowbound.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(
        days=int(os.environ.get("SESSION_LIFETIME_DAYS", 7))
    )

    SMTP_HOST = os.environ.get("SMTP_HOST", "")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASS = os.environ.get("SMTP_PASS", "")
    SMTP_FROM = os.environ.get("SMTP_FROM", "info@69hawn.com")
    MAGIC_LINK_EXPIRY_MINUTES = int(os.environ.get("MAGIC_LINK_EXPIRY_MINUTES", 15))
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "larry@kamons.com")
    # When set, all outgoing emails are redirected here instead of the real recipient.
    # Useful for testing — set to empty string in production.
    TEST_EMAIL_OVERRIDE = os.environ.get("TEST_EMAIL_OVERRIDE", "")
    # Testing mode: suppresses trade notification emails and widens the
    # week dropdown range to today-3 … today+3 years (vs. today-1 … today+3).
    TESTING_MODE = os.environ.get("TESTING_MODE", "false").lower() in ("true", "1", "yes")
