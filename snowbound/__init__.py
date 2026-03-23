from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)

    from .config import Config
    app.config.from_object(Config)
    app.config["PERMANENT_SESSION_LIFETIME"] = Config.PERMANENT_SESSION_LIFETIME

    db.init_app(app)

    from .routes.calendar import bp as calendar_bp
    from .routes.form import bp as form_bp
    from .routes.auth import bp as auth_bp
    from .routes.ics import bp as ics_bp
    from .routes.email_compose import bp as email_bp
    from .routes.admin import bp as admin_bp

    app.register_blueprint(calendar_bp)
    app.register_blueprint(form_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(ics_bp)
    app.register_blueprint(email_bp)
    app.register_blueprint(admin_bp)

    with app.app_context():
        db.create_all()
        _create_views()
        _seed_fk_overrides()

    return app


def _seed_fk_overrides():
    """Ensure fk_overrides rows exist for columns that can't be auto-detected by convention."""
    from .models import FkOverride
    overrides = [
        ("trade_detail", "current_holder_id", "owners"),
    ]
    for table_name, column_name, ref_table in overrides:
        exists = db.session.execute(
            db.text(
                "SELECT 1 FROM fk_overrides WHERE table_name=:t AND column_name=:c"
            ),
            {"t": table_name, "c": column_name},
        ).fetchone()
        if not exists:
            db.session.execute(
                db.text(
                    "INSERT INTO fk_overrides (table_name, column_name, ref_table) "
                    "VALUES (:t, :c, :r)"
                ),
                {"t": table_name, "c": column_name, "r": ref_table},
            )
    db.session.commit()


def _create_views():
    sql = db.engine.connect()
    views = [
        ("v_previous_year", "CAST(strftime('%Y', 'now') AS INTEGER) - 1"),
        ("v_current_year",  "CAST(strftime('%Y', 'now') AS INTEGER)"),
        ("v_next_year",     "CAST(strftime('%Y', 'now') AS INTEGER) + 1"),
    ]
    for view_name, year_expr in views:
        sql.execute(db.text(f"""
            CREATE VIEW IF NOT EXISTS {view_name} AS
            SELECT o.display_info, td.week_start, td.comment, td.calculated_owner
            FROM trade_detail td
            JOIN owners o ON td.owner_id = o.id
            WHERE td.year = {year_expr}
            ORDER BY td.week_start
        """))
    sql.commit()
    sql.close()
