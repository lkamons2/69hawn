# Phase 1 — Infrastructure Setup

## Goal

Get a working Flask app running locally in VSCode with the correct database schema, session management, and project structure in place. No data, no business logic yet — just the skeleton everything else will plug into.

PythonAnywhere deployment happens in Phase 5 (Cutover), not here.

## Tasks

### 1.1 Local Python Environment

- [ ] Create a virtual environment in the project folder:
  ```bash
  python -m venv .venv
  ```
- [ ] Activate it (VSCode should pick this up automatically as the interpreter)
- [ ] Install dependencies:
  ```bash
  pip install flask flask-sqlalchemy icalendar python-dotenv
  pip freeze > requirements.txt
  ```

### 1.2 Project Structure

Create the following layout inside `c:\lak\projects\py\69hawn\`:

```
snowbound/
├── app.py                  # Flask app factory
├── config.py               # Config from .env
├── models.py               # SQLAlchemy models
├── routes/
│   ├── __init__.py
│   ├── calendar.py
│   ├── form.py
│   ├── auth.py
│   ├── ics.py
│   ├── email_compose.py
│   └── admin.py
├── templates/
│   ├── base.html
│   ├── calendar.html
│   ├── form.html
│   ├── login.html
│   ├── ics.html
│   ├── email.html
│   └── admin/
│       └── table.html
├── static/
│   └── style.css
├── scripts/
│   ├── generate_rotation.py    # Seeds calendar + mud_weeks tables
│   ├── seed_owners.py          # Seeds owners + owner_emails
│   ├── import_trade_detail.py  # One-time CSV import
│   ├── import_audit.py         # One-time CSV import
│   └── verify_counts.py        # Row count check
├── .env                    # Secrets — NOT committed to git
├── .gitignore
├── requirements.txt
└── snowbound.db            # SQLite file — gitignored
```

### 1.3 Environment Config (`.env`)

```
SECRET_KEY=<generate a random string — any long random text>
DATABASE_URL=sqlite:///snowbound.db
SMTP_HOST=<smtp server>
SMTP_PORT=587
SMTP_USER=<email address>
SMTP_PASS=<password>
SMTP_FROM=info@69hawn.com
MAGIC_LINK_EXPIRY_MINUTES=15
SESSION_LIFETIME_DAYS=7
ADMIN_EMAIL=larry@kamons.com
```

Add `.env` and `snowbound.db` to `.gitignore`.

### 1.4 SQLite Schema

Create all tables in `models.py` (SQLAlchemy) or as raw SQL in an `init_db.py` script:

**Tables to create:**
- `owners`
- `owner_emails`
- `calendar`
- `mud_weeks`
- `trade_detail`
- `audit`
- `magic_links`
- `site_config`
- `field_definitions`
- `lov_values`

**Views to create:**
```sql
CREATE VIEW v_previous_year AS
SELECT o.display_info, td.week_start, td.comment, td.calculated_owner
FROM trade_detail td
JOIN owners o ON td.owner_id = o.id
WHERE td.year = CAST(strftime('%Y', 'now') AS INTEGER) - 1
ORDER BY td.week_start;

CREATE VIEW v_current_year AS ...  -- same with +0
CREATE VIEW v_next_year AS ...     -- same with +1
```

See [CLAUDE.md](../CLAUDE.md) for full column definitions.

### 1.5 Session Management

- Flask `session` with `SECRET_KEY`
- Set `PERMANENT_SESSION_LIFETIME` to 7 days
- Session stores: `owner_id`, `owner_short_name`, `is_admin`
- Helper: `@login_required` decorator that checks `session.get('owner_id')`
- Helper: `@admin_required` decorator that also checks `session.get('is_admin')`

### 1.6 Local Smoke Test

Run with:
```bash
flask --app app run --debug
```

- [ ] App starts without errors at `http://localhost:5000`
- [ ] `GET /` returns a 200 with a placeholder page
- [ ] Database file `snowbound.db` created on first run
- [ ] All tables exist (`SELECT name FROM sqlite_master WHERE type='table'`)

## Deliverables

- Flask app runs locally in VSCode
- SQLite database with correct schema (empty)
- `.env` config in place
- `requirements.txt` committed
- Project structure matching the layout above

## Next Phase

[Phase 2 — Seed Database](phase-2-seed-database.md)
