# Phase 3 — Build Core Routes

## Goal

Build all user-facing routes in priority order. Start with the calendar view (visible, verifiable, no auth needed) and work toward the form (most complex). Each route should be fully functional and tested before moving to the next.

## Notes from Phase 2

### Running the app locally
Use the venv Python explicitly — system Python doesn't have Flask installed:
```bash
.venv/Scripts/python -m flask --app app run --debug   # Windows
# or activate the venv first: source .venv/Scripts/activate
```

### Loyle has two rotation slots — critical for the calendar view
Loyle appears in rotation position 1 **and** position 10, giving them ~10 weeks/year (double any other owner). In the Google Sheet the calendar grid shows **10 rows** (one per rotation slot), so Loyle appears as **two separate rows**.

The database has a single `owner_id` for Loyle, so `trade_detail` returns ~10 Loyle rows when queried for a year. The `week_number` column cannot distinguish slot-1 weeks from slot-10 weeks (both are numbered 1–5 independently).

**How to build the calendar view correctly:**
1. Query `trade_detail` for the year, joined with `owners`, ordered by `week_start` (ascending).
2. Group rows by `owner_id`, preserving chronological order within each owner.
3. Chunk each owner's weeks into groups of **up to 5** — this naturally produces two rows for Loyle and one row for everyone else.
4. Sort the resulting display-rows by the **first `week_start`** of each chunk. This gives the same row order as the Google Sheet (chronological by rotation entry date, not alphabetical).
5. Render each chunk as one `<tr>` in the grid.

This approach requires no schema changes and handles Smith's occasional 4-week year (last slot in years with 49 non-mud Thursdays) automatically.

**2026 row order for reference (from CurrentYear sheet):**
Boone → Kamons → Mitchell → Loyle (slot 1) → Loyle (slot 10) → Zerfas → Sproul → Miller → Stalker → Smith

### What's already implemented in route stubs
- `snowbound/decorators.py` — `login_required` and `admin_required` are complete.
- `routes/auth.py` — ~90% done: token generation, token validation, session-setting, logout all work. **Only missing:** actual SMTP email sending (currently shows the magic link as a dev flash message). In dev mode this is usable as-is.
- `routes/calendar.py` — URL routing stubs are correct (including `/lookup`). Templates and query logic are missing.
- All other routes (`form.py`, `ics.py`, `email_compose.py`, `admin.py`) are empty stubs that return placeholder text.

### Data observations from Phase 2
- `trade_detail` has 3,921 rows; 73 are traded (`is_traded = 1`).
- `calculated_owner` is the denormalized current-holder name used for display. Update it on every trade.
- Existing comment format in the data: `"traded to Loyle for 01/23/2025"`, `"Using Condo"`, `"Not Using"`. Match this convention when writing new trades.
- `current_holder_id` defaults to `owner_id` (never NULL) for untraded rows — queries can safely join on it.
- `week_start` is always a `MM/DD/YYYY` string (Thursday). Compute end date in Python: `datetime.strptime(week_start, "%m/%d/%Y") + timedelta(days=6)`.
- Smith gets 4 weeks in years where the last rotation slot runs short (49 non-mud Thursdays ÷ 10 owners). Templates must handle rows with fewer than 5 week cells.

### SMTP / email in development
`routes/auth.py` currently flashes the magic link URL as a dev convenience instead of sending email. This is intentional — leave it as-is until SMTP credentials are configured in `.env`. Do not remove the flash; it makes local testing possible without email infrastructure.

---

## Build Order

1. `/calendar` — read-only, public, easiest to verify visually
2. `/ics` — self-contained, no auth, easy to test
3. `/login` + `/auth` — needed before any auth-required routes
4. `/form` — most complex, depends on auth
5. `/email` — straightforward port of existing JS
6. `/admin/table` — generic table browser (Larry's admin tool)

---

## Route 1 — Calendar View (`/calendar`)

**File:** `routes/calendar.py`

### Routes
```
GET /calendar             → current year
GET /calendar/<year>      → specific year
GET /calendar/prev        → year - 1 (relative to current)
GET /calendar/next        → year + 1 (relative to current)
```

### Query
```sql
SELECT td.week_start, td.comment, td.calculated_owner, td.is_traded,
       td.current_holder_id, o.display_info
FROM trade_detail td
JOIN owners o ON td.owner_id = o.id
WHERE td.year = :year
ORDER BY o.id, td.week_start
```

### Template (`templates/calendar.html`)

Must match the existing Google Sheets layout owners are used to:

- **Row 1-3:** Property info pulled from `site_config` (Garage, WiFi, Lock Box — each with its `note` field)
- **Row 4:** Headers: Owner Info | WEEK 1 | WEEK 2 | WEEK 3 | WEEK 4 | WEEK 5
- **Rows 5+:** One row per owner:
  - Column A: `display_info` (multi-line contact block)
  - Columns B-F: `"MM/DD/YYYY - MM/DD/YYYY"` (Thursday to Wednesday, 7 days)
    - Week end date = week_start date + 6 days
    - Below date range: trade comment if any (e.g., "traded to Loyle for 01/23/2025")
- Previous / Next year buttons at top
- Year picker dropdown (reasonable range, e.g., 2022-2030)
- Mobile responsive — works on phones and tablets (elderly users!)

### Verification
- [ ] Current year renders correctly
- [ ] Dates match the Google Sheet calendar view for the same year
- [ ] Trade comments appear under the correct weeks
- [ ] Previous/Next navigation works
- [ ] Renders correctly on mobile

---

## Route 2 — ICS Download (`/ics`)

**File:** `routes/ics.py`

### Routes
```
GET  /ics              → form: select owner, select year
POST /ics/download     → generate and serve .ics file
```

### Form Fields
- Owner (dropdown from `owners` table, active only)
- Year (dropdown, reasonable range)

### ICS Generation
```python
from icalendar import Calendar, Event
from datetime import date, timedelta

# For each week in trade_detail for owner+year:
#   - Parse week_start (MM/DD/YYYY)
#   - Create VEVENT: DTSTART=week_start, DTEND=week_start+7days
#   - SUMMARY: "Snowbound Condo - {owner_name}"
#   - DESCRIPTION: comment if any

# Return as file download
# Content-Type: text/calendar
# Content-Disposition: attachment; filename="snowbound-{owner}-{year}.ics"
```

### Verification
- [ ] Download a file, import into Google Calendar or Apple Calendar
- [ ] Events appear on correct Thursdays
- [ ] Week spans Thursday to Wednesday (7 nights)
- [ ] Compare event dates against the Google Sheet for the same owner/year

---

## Route 3 — Authentication (`/login`, `/auth/<token>`, `/logout`)

**File:** `routes/auth.py`

### Magic Link Flow

```
GET  /login           → show email input form
POST /login           → validate email, send magic link, show "check your email"
GET  /auth/<token>    → validate token, set session, redirect to /form
GET  /logout          → clear session, redirect to /calendar
```

### Login Logic
1. Accept email input
2. Lowercase + strip whitespace
3. Look up in `owner_emails` — if not found, show generic message (don't reveal whether email exists)
4. If found: generate `secrets.token_urlsafe(32)`, store in `magic_links` with 15-min expiry
5. Send email via SMTP with link: `https://<domain>/auth/<token>`
6. Show: "If this email is registered, you'll receive a link shortly."

### Token Validation (`/auth/<token>`)
1. Look up token in `magic_links`
2. Check: exists, not expired (`expires_at > now`), not used
3. If valid: mark `used=1`, set session (`owner_id`, `short_name`, `is_admin`), redirect to `/form`
4. If invalid/expired: show error with link back to `/login`

### Session
```python
session.permanent = True
app.permanent_session_lifetime = timedelta(days=7)
session['owner_id'] = owner.id
session['owner_name'] = owner.short_name
session['is_admin'] = owner.is_admin
```

### Decorators
```python
def login_required(f):
    # redirect to /login if session['owner_id'] missing

def admin_required(f):
    # redirect to /calendar if not is_admin
```

### SMTP Sending
```python
import smtplib
from email.mime.text import MIMEText

# Use config from .env: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM
```

### Verification
- [ ] Enter a valid email → receive email with link
- [ ] Click link → session set, redirected to /form
- [ ] Expired link → error message shown
- [ ] Used link → error message shown
- [ ] Unknown email → same generic message as valid email (no info leak)
- [ ] `/logout` clears session

---

## Route 4 — Trade Form (`/form`)

**File:** `routes/form.py`

### Routes
```
GET  /form    → render form (auth required)
POST /form    → process submission (auth required)
```

### Form Fields (from `GAS-code/Form.html`)
- **Trade Type** (radio): Trade Week | Give Away | Not Using | Comment
- **Owner 1** (dropdown): populated from `owners`; defaults to logged-in owner
- **Owner 1 Week** (dropdown): weeks belonging to Owner 1 for the current/next year
- **Owner 2** (dropdown, conditional): shown only for "Trade Week" and "Give Away"
- **Owner 2 Week** (dropdown, conditional): weeks belonging to Owner 2; shown for "Trade Week"
- **Comment** (text, ≤40 chars): shown for "Comment", optional for others

### Week Dropdown Population
Weeks shown in Owner 1/2 week dropdowns come from `trade_detail`:
```sql
SELECT td.week_start, td.calculated_owner
FROM trade_detail td
WHERE td.owner_id = :owner_id AND td.year IN (:current_year, :next_year)
ORDER BY td.week_start
```
Display as: `"MM/DD/YYYY (currently: {calculated_owner})"` so owners can see current state.

### POST Processing Logic
```
1. Validate session
2. Validate inputs:
   - trade_type is one of the four valid values
   - owner1 and owner1_week exist and are consistent
   - If "Trade Week": owner2 and owner2_week required and consistent
   - comment ≤ 40 chars
3. Apply trade_type:
   - "Trade Week":
       UPDATE trade_detail SET current_holder_id=owner2, is_traded=1,
              calculated_owner=owner2.short_name, trade_date=now,
              trade_history=trade_history||'→'||owner2.short_name,
              comment=:comment
       WHERE week_start=owner1_week AND owner_id=owner1
       -- and reciprocal for owner2_week
   - "Give Away":
       UPDATE trade_detail SET current_holder_id=owner2, is_traded=1,
              calculated_owner=owner2.short_name, trade_date=now,
              trade_history=...
       WHERE week_start=owner1_week AND owner_id=owner1
   - "Not Using":
       UPDATE trade_detail SET comment='Not Using', trade_date=now
       WHERE week_start=owner1_week AND owner_id=owner1
   - "Comment":
       UPDATE trade_detail SET comment=:comment, trade_date=now
       WHERE week_start=owner1_week AND owner_id=owner1
4. Write audit row
5. Show success confirmation with summary of what was changed
```

### Verification
- [ ] Each trade type submits and updates the database correctly
- [ ] Audit row written for every submission
- [ ] Week dropdowns only show this owner's weeks
- [ ] Comment truncated/rejected if > 40 chars
- [ ] Cross-check a test trade in trade_detail vs what the GAS app would have done (Phase 4)

---

## Route 5 — Email Compose (`/email`)

**File:** `routes/email_compose.py`

### Route
```
GET /email    → compose URL page (auth required)
```

### Logic (port from `GAS-code/Email.html`)
1. Query all active owner emails from `owner_emails`
2. Build a comma-separated list of all email addresses
3. Render page with:
   - "Open in Gmail" button → `https://mail.google.com/mail/?view=cm&to={emails}`
   - "Open in Outlook" button → `mailto:{emails}`
   - "Copy to Clipboard" button → JS clipboard copy of the email list

### Verification
- [ ] All 10 owners' emails appear in the list
- [ ] Gmail compose URL opens with correct recipients
- [ ] Clipboard copy works

---

## Route 6 — Admin Table Browser (`/admin/table/<table_name>`)

**File:** `routes/admin.py`

See [generic-table-browser-requirements.md](../generic-table-browser-requirements.md) for the full spec.

### Summary
- Single route handles any table or view by name
- Columns discovered via `PRAGMA table_info()`
- Views auto-detected → read-only (no CRUD)
- Client-side multi-column sort
- CSV export
- `h=` convention for section headers in views
- CRUD (Add/Edit/Delete) for regular tables
- Progressive enhancement via `field_definitions` and `lov_values`

### Tables Larry will use this for
- `owners` — manage the 10 owners
- `owner_emails` — manage email addresses
- `site_config` — update garage code, WiFi password, lock box code
- `trade_detail` — browse/review all trades
- `audit` — review submission history
- `v_current_year` / `v_previous_year` / `v_next_year` — read-only year views

### Verification
- [ ] Browse each table without errors
- [ ] Sort columns (single and multi-column)
- [ ] Export CSV for a table
- [ ] Add a row to `site_config`, verify it appears
- [ ] Edit a row, verify the change
- [ ] Delete a row, verify it's gone
- [ ] Views are read-only (no Add/Edit/Delete buttons)
- [ ] `h=` rows render as section headers

---

## Next Phase

[Phase 4 — Parallel Testing](phase-4-parallel-testing.md)
