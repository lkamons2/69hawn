from datetime import datetime
from . import db


class Owner(db.Model):
    __tablename__ = "owners"

    id = db.Column(db.Integer, primary_key=True)
    short_name = db.Column(db.Text, nullable=False, unique=True)
    full_name = db.Column(db.Text)
    phone = db.Column(db.Text)
    display_info = db.Column(db.Text)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)

    emails = db.relationship("OwnerEmail", backref="owner", lazy=True)


class OwnerEmail(db.Model):
    __tablename__ = "owner_emails"

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("owners.id"), nullable=False)
    email = db.Column(db.Text, nullable=False)
    is_primary = db.Column(db.Boolean, default=False)


class Calendar(db.Model):
    __tablename__ = "calendar"

    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("owners.id"), nullable=False)
    week_start = db.Column(db.Text, nullable=False)  # MM/DD/YYYY
    week_number = db.Column(db.Integer)  # 1-5 within owner's allocation

    owner = db.relationship("Owner", backref="calendar_weeks")


class MudWeek(db.Model):
    __tablename__ = "mud_weeks"

    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    week_start = db.Column(db.Text, nullable=False)  # MM/DD/YYYY
    num_mud_weeks = db.Column(db.Integer)  # 3 or 4
    num_thursdays = db.Column(db.Integer)  # 52 or 53


class TradeDetail(db.Model):
    __tablename__ = "trade_detail"

    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("owners.id"), nullable=False)
    week_start = db.Column(db.Text, nullable=False)  # MM/DD/YYYY
    is_traded = db.Column(db.Boolean, default=False)
    current_holder_id = db.Column(db.Integer, db.ForeignKey("owners.id"))
    trade_date = db.Column(db.DateTime)
    trade_history = db.Column(db.Text)  # e.g. "Sproul->Miller"
    comment = db.Column(db.Text)
    audit_trail = db.Column(db.Text)
    calculated_owner = db.Column(db.Text)  # denormalized for display

    owner = db.relationship("Owner", foreign_keys=[owner_id], backref="trade_weeks")
    current_holder = db.relationship("Owner", foreign_keys=[current_holder_id])


class Audit(db.Model):
    __tablename__ = "audit"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    email = db.Column(db.Text)
    trade_type = db.Column(db.Text)  # "Trade Week", "Give Away", "Not Using", "Comment"
    owner1 = db.Column(db.Text)
    owner1_week = db.Column(db.Text)
    owner2 = db.Column(db.Text)
    owner2_week = db.Column(db.Text)
    comment = db.Column(db.Text)
    result1 = db.Column(db.Text)
    result2 = db.Column(db.Text)


class MagicLink(db.Model):
    __tablename__ = "magic_links"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.Text, nullable=False)
    token = db.Column(db.Text, nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)


class SiteConfig(db.Model):
    __tablename__ = "site_config"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.Text, nullable=False)
    value = db.Column(db.Text)
    note = db.Column(db.Text)


class FieldDefinition(db.Model):
    __tablename__ = "field_definitions"

    id = db.Column(db.Integer, primary_key=True)
    table_name = db.Column(db.Text, nullable=False)
    column_name = db.Column(db.Text, nullable=False)
    display_name = db.Column(db.Text, nullable=False)
    field_type = db.Column(db.Text, default="text")  # text|checkbox|textarea|date|select
    display_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Integer, default=1)
    lov_name = db.Column(db.Text, default="")


class LovValue(db.Model):
    __tablename__ = "lov_values"

    id = db.Column(db.Integer, primary_key=True)
    lov_name = db.Column(db.Text, nullable=False)
    value = db.Column(db.Text, default="")
    display_label = db.Column(db.Text, default="")
    display_order = db.Column(db.Integer, default=0)
    query = db.Column(db.Text, default="")


class FkOverride(db.Model):
    __tablename__ = "fk_overrides"

    id = db.Column(db.Integer, primary_key=True)
    table_name = db.Column(db.Text, nullable=False)
    column_name = db.Column(db.Text, nullable=False)
    ref_table = db.Column(db.Text, nullable=False)  # table to link to
