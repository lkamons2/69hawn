# CLAUDE.md — Snowbound LLC Condo Calendar App Migration

## Project Summary

Migrating a Google Apps Script (GAS) + Google Sheets application to Python/Flask on PythonAnywhere. The app manages a shared condo calendar for ~10 owner families in Breckenridge, CO. Owners rotate through Thursday-to-Thursday weeks at the condo, and the app handles trading weeks, marking weeks as unused, and generating calendar views.

## Why We're Migrating

A long-standing Chromium bug breaks GAS web apps when users are logged into multiple Google accounts. The app only works in incognito mode, which is unacceptable for the mostly elderly user base. This is a Google platform limitation with no code-level fix — it's been open on Google's issue tracker since 2017.

## Current Architecture (Being Replaced)

### Google Sheets ("database") — 13 sheets:
- **Calendar to 2100** — Master rotation schedule, 10 owners × ~80 years, ~800 rows
- **Mud Weeks** — 3-4 skip weeks per year (first Thursdays in May), ~80 rows
- **TradeDetail** — One row per owner-week with trade tracking, ~3,900 rows
- **NameList** — 10 owners with up to 3 emails each, phone numbers, contact info
- **Audit** — Form submission log, ~106 rows
- **TradeDetailFiltered** — View of only traded weeks (will become a SQL view)
- **PreviousYear / CurrentYear / NextYear / TestYear** — Year-at-a-glance formatted views (will become Flask template + SQL views)
- **SQL** — Original Oracle PL/SQL reference (documentation only)
- **README** — Notes about date formatting requirements
- **Debug** — processForm execution log

### Google Apps Script files:
- **Code.js** — doGet router, form processing, caching, owner/week lookups
- **generateCondoCalendar.js** — Rotation generation (has Python version in comments!)
- **mailFunctions.js** — Mailjet email sending (BEING DROPPED)
- **LarrysCode.js** — Trade processing, email validation, audit logging
- **MenuCode.js** — Google Sheets custom menu (BEING DROPPED)
- **Form.html** — Trade/comment submission form
- **FormICS.html** — ICS calendar file download form
- **Email.html** — Compose URL generator for Gmail/Outlook

### Key business logic:
- 10 owners rotate through Thursday weeks each year
- "Mud weeks" (3-4 weeks in May) are skipped — no one uses the condo
- Years with 53 Thursdays get 4 mud weeks; 52-Thursday years get 3
- Rotation carries over year to year (last owner index persists)
- Owners can: Trade weeks with each other, Give away a week, Mark a week as Not Using, or add a Comment
- All dates stored as MM/DD/YYYY text format (10 digits with leading zeros)
- The rotation data is pre-generated from 2022 to 2100

## New Architecture

### Tech Stack
- **Hosting:** PythonAnywhere (free tier to start, $5/month if custom domain or unrestricted SMTP needed)
- **Framework:** Flask
- **Database:** SQLite (via SQLAlchemy) — data volume is tiny, single-user writes
- **Templates:** Jinja2
- **CSS:** Simple/minimal (elderly users, must work on phones/tablets)
- **Auth:** Magic link (email + token) — no passwords, no accounts to create
- **Email sending:** SMTP for magic links only (no Mailjet)
- **ICS generation:** Python `icalendar` library
- **Admin:** Generic Table Browser component (see below)

### Routes
```
GET  /login .................. Enter email → receive magic link
GET  /auth/<token> ........... Verify magic link → set session
GET  /logout ................. Clear session

GET  /calendar ............... Year grid view, defaults to current year (PUBLIC)
GET  /calendar/<year> ........ Year grid view for specific year (PUBLIC)
GET  /calendar/prev .......... Previous year shortcut (PUBLIC)
GET  /calendar/next .......... Next year shortcut (PUBLIC)
GET  /lookup ................. Owner lookup — pick owner + year/month for flat list (PUBLIC)

GET  /form ................... Trade/comment submission form (AUTH REQUIRED)
POST /form ................... Process trade submission (AUTH REQUIRED)
GET  /email .................. Compose URL page for Gmail/Outlook (AUTH REQUIRED)

GET  /ics .................... ICS download form (PUBLIC)
POST /ics/download ........... Generate and serve .ics file (PUBLIC)

GET  /admin/table/<name> ..... Generic table browser (ADMIN ONLY — Larry)
GET  /admin/export ........... Export data to Excel (ADMIN ONLY)
```

### Database Schema

**owners**
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| short_name | TEXT NOT NULL UNIQUE | "Kamons", "Loyle", etc. |
| full_name | TEXT | "Larry & Maureen Kamons" |
| phone | TEXT | Phone number(s), free-form |
| display_info | TEXT | Full contact block for calendar views |
| is_admin | BOOLEAN DEFAULT 0 | Larry = 1 |
| is_active | BOOLEAN DEFAULT 1 | Soft delete |

**owner_emails**
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| owner_id | INTEGER FK → owners.id | |
| email | TEXT NOT NULL | Lowercase, trimmed |
| is_primary | BOOLEAN DEFAULT 0 | Primary contact email |

**calendar**
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| year | INTEGER NOT NULL | |
| owner_id | INTEGER FK → owners.id | Original rotation owner |
| week_start | TEXT NOT NULL | "MM/DD/YYYY" format (Thursday) |
| week_number | INTEGER | 1-5 within the owner's year allocation |

**mud_weeks**
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| year | INTEGER NOT NULL | |
| week_start | TEXT NOT NULL | "MM/DD/YYYY" format |
| num_mud_weeks | INTEGER | 3 or 4 |
| num_thursdays | INTEGER | 52 or 53 |

**trade_detail**
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| year | INTEGER NOT NULL | |
| owner_id | INTEGER FK → owners.id | Original scheduled owner |
| week_start | TEXT NOT NULL | "MM/DD/YYYY" |
| is_traded | BOOLEAN DEFAULT 0 | |
| current_holder_id | INTEGER FK → owners.id | Who actually has the condo |
| trade_date | DATETIME | When the trade was recorded |
| trade_history | TEXT | "Sproul->Miller" |
| comment | TEXT | Max 40 chars in the form |
| audit_trail | TEXT | |
| calculated_owner | TEXT | Denormalized for easy display |

**audit**
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| timestamp | DATETIME DEFAULT CURRENT_TIMESTAMP | |
| email | TEXT | Who submitted |
| trade_type | TEXT | "Trade Week", "Give Away", "Not Using", "Comment" |
| owner1 | TEXT | |
| owner1_week | TEXT | |
| owner2 | TEXT | Nullable |
| owner2_week | TEXT | Nullable |
| comment | TEXT | |
| result1 | TEXT | Audit record for first side of trade |
| result2 | TEXT | Audit record for second side |

**magic_links**
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| email | TEXT NOT NULL | |
| token | TEXT NOT NULL UNIQUE | Random URL-safe token |
| created_at | DATETIME DEFAULT CURRENT_TIMESTAMP | |
| expires_at | DATETIME | created_at + 15 minutes |
| used | BOOLEAN DEFAULT 0 | One-time use |

**site_config** (replaces hardcoded Garage/WiFi/Lock Box values)
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| key | TEXT NOT NULL | "Garage", "WiFi", "Lock Box" |
| value | TEXT | "2071", "9706683418", "4926" |
| note | TEXT | "#67 Patsy and Doug Lange h: 303-791-7521..." |

**field_definitions** (for Generic Table Browser)
```sql
CREATE TABLE IF NOT EXISTS field_definitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,
    column_name TEXT NOT NULL,
    display_name TEXT NOT NULL,
    field_type TEXT DEFAULT 'text',      -- text|checkbox|textarea|date|select
    display_order INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,         -- 0 = hide column
    lov_name TEXT DEFAULT ''             -- links to lov_values for dropdowns
);
```

**lov_values** (for Generic Table Browser dropdowns)
```sql
CREATE TABLE IF NOT EXISTS lov_values (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lov_name TEXT NOT NULL,
    value TEXT DEFAULT '',
    display_label TEXT DEFAULT '',
    display_order INTEGER DEFAULT 0,
    query TEXT DEFAULT ''                -- if populated, execute SQL instead of static rows
);
```

### SQL Views (replace the PreviousYear/CurrentYear/NextYear sheets)
```sql
CREATE VIEW v_current_year AS
SELECT o.display_info, td.week_start, td.comment, td.calculated_owner
FROM trade_detail td
JOIN owners o ON td.owner_id = o.id
WHERE td.year = CAST(strftime('%Y', 'now') AS INTEGER)
ORDER BY td.week_start;
```
Same pattern with -1 and +1 for previous/next year. These show up in the Generic Table Browser as read-only reports automatically.

## Calendar View Requirements

### View 1 — Year Grid (primary view, PUBLIC)
Must match the existing Google Sheets format the owners are used to:
- **Rows 1-3:** Property info (Garage code + neighbor info, WiFi password + neighbor info, Lock Box code) — pulled from `site_config` table
- **Row 4:** Headers: Owner Info | WEEK 1 | WEEK 2 | WEEK 3 | WEEK 4 | WEEK 5
- **Rows 5+:** Each owner gets one row:
  - Column A: Multi-line contact block (name, email(s), phone) from `owners.display_info`
  - Columns B-F: Each week cell shows "MM/DD/YYYY - MM/DD/YYYY" (start - end date range) with trade comment below (e.g., "traded to Loyle for 01/23/2025")
- Default to current year with Previous/Next buttons and a year picker dropdown
- Mobile responsive

### View 2 — Owner Lookup (PUBLIC)
- Pick an owner (or "All"), pick a year or month/year range
- Flat tabular list: one row per week showing date, original owner, current holder, comments
- "When's my next week?" view for individual owners

## Generic Table Browser

A reusable Flask component included in this app. See `generic-table-browser-requirements.md` for full spec. Key features:
- Single route: `GET /admin/table/<table_name>`
- Discovers columns at runtime from `PRAGMA table_info()`
- Views detected automatically → read-only (no CRUD)
- Client-side sorting with shift-click multi-column sort
- CSV export
- `h=` convention for section headers in SQL views
- CRUD for tables (Add/Edit/Delete)
- Progressive enhancement via `field_definitions` and `lov_values`
- Larry uses this to manage owners, site_config, and browse all data

## Authentication — Magic Link Flow
1. User visits /login
2. Enters email address
3. Server checks email exists in `owner_emails` table
4. If yes: generate token, store in `magic_links`, send email with link
5. User clicks link → /auth/<token>
6. Server validates token (not expired, not used), sets Flask session
7. Session lasts 7 days
8. SMTP sending through 69hawn.com domain (for magic links only)

## Key Design Decisions
- **Mailjet dropped entirely** — was unnecessary, caused DMARC issues. Email compose URLs (Gmail/Outlook/copy to clipboard) already exist and work better since emails come from actual owners.
- **SQLite not MySQL** — data volume is tiny, single-user writes, file-based backup, works on PythonAnywhere free tier
- **site_config table instead of .env for property info** — Garage code, WiFi, Lock Box editable by Larry via Generic Table Browser, no code changes needed
- **Dates stay as MM/DD/YYYY text** — matches existing format, avoids conversion issues during migration
- **Python rotation generator already exists** — commented out in generateCondoCalendar.js, just needs minor tweaks
- **Calendar data pre-generated to 2100** — static data, seeded once

## Config (.env — secrets only, NOT property info)
```
SECRET_KEY=<random-string>
DATABASE_URL=sqlite:///snowbound.db
SMTP_HOST=<smtp-server>
SMTP_PORT=587
SMTP_USER=<email>
SMTP_PASS=<password>
SMTP_FROM=info@69hawn.com
MAGIC_LINK_EXPIRY_MINUTES=15
SESSION_LIFETIME_DAYS=7
ADMIN_EMAIL=larry@kamons.com
```

## Migration Phases

### Phase 1: Infrastructure
- PythonAnywhere account
- Flask app skeleton with SQLAlchemy
- SQLite database with schema
- Session management

### Phase 2: Seed Database
- owners + owner_emails: manual entry from NameList (only 10 owners)
- calendar + mud_weeks: run Python rotation generator (already written)
- trade_detail: CSV export from sheet → Python import script
- audit: CSV export → import
- Verify row counts match

### Phase 3: Build Core Routes
- /calendar (year grid view) — easiest, most visible
- /ics (calendar download)
- /login + /auth (magic link)
- /form (trade submission) — most complex
- /email (compose URLs)
- /admin/table (generic table browser)

### Phase 4: Parallel Testing
- Run both apps simultaneously
- Larry tests all operations
- Compare data between sheet and database

### Phase 5: Cutover
- Final data sync
- Point users to new URL
- Keep GAS app read-only for 30 days

## Source Files
The following files from the original GAS app are available for reference:
- `Code.js` — main router and form processing
- `generateCondoCalendar.js` — rotation logic (Python version in comments)
- `mailFunctions.js` — Mailjet integration (being dropped, reference only)
- `LarrysCode.js` — trade processing logic
- `MenuCode.js` — Sheets menu (being dropped)
- `Form.html` — trade submission form
- `FormICS.html` — ICS download form
- `Email.html` — compose URL page
- `SnowBoundersCalendarApp.xlsx` — exported Google Sheet (the "database")
- `generic-table-browser-requirements.md` — full spec for the admin table browser component
