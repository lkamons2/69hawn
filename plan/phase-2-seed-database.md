# Phase 2 — Seed Database

## Goal

Populate the SQLite database with all data from the Google Sheet export. After this phase the database should be a faithful replica of the current sheet data, verified by row count checks.

## Notes from Phase 1

- **Database location** — `snowbound.db` is created relative to where you run `flask`, so always run scripts from `c:\lak\projects\py\69hawn\`.
- **Use the app context in scripts** — import the Flask app to reuse the same SQLAlchemy session:
  ```python
  import sys, os
  sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
  from snowbound import create_app, db
  from snowbound.models import Owner, Calendar  # etc.

  app = create_app()
  with app.app_context():
      # do inserts here
  ```
- **`trade_detail.year` is an integer** — if the CSV doesn't have a separate year column, extract it from `week_start` with `int(week_start[-4:])`.
- **`current_holder_id` should default to `owner_id`** — for untraded rows, set `current_holder_id = owner_id` (not NULL) so the calendar view doesn't need to handle NULLs. Confirm against the sheet before writing the import.
- **Exporting CSVs from the `.xlsx`** — open `GAS-code/SnowBoundersCalendarApp.xlsx` in Excel, select each sheet, then File → Save As → CSV.

## Prerequisites

- Phase 1 complete (schema in place)
- `SnowBoundersCalendarApp.xlsx` available (already in `GAS-code/`)
- Export the following sheets to CSV before starting:
  - `TradeDetail` → `scripts/data/trade_detail.csv`
  - `Audit` → `scripts/data/audit.csv`
  - `NameList` → `scripts/data/name_list.csv` (or enter manually — only 10 owners)

## Tasks

### 2.1 Owners + Owner Emails (Manual Entry Preferred)

Only 10 owners — manual entry is safer than CSV parsing for contact data.

For each owner, insert into `owners`:
- `short_name` — "Kamons", "Loyle", etc.
- `full_name` — "Larry & Maureen Kamons"
- `phone` — free-form
- `display_info` — full contact block as it appears in the calendar grid
- `is_admin` — 1 for Larry Kamons, 0 for everyone else
- `is_active` — 1 for all active owners

For each email address per owner, insert into `owner_emails`:
- `owner_id` — FK to owner
- `email` — lowercase, trimmed
- `is_primary` — 1 for main contact email

**Verification:** 10 rows in `owners`, ~20-25 rows in `owner_emails` (owners have 1-3 emails each).

### 2.2 Calendar + Mud Weeks (Python Rotation Generator)

The rotation generator already exists in commented Python inside `GAS-code/generateCondoCalendar.js`. Extract it to `scripts/generate_rotation.py`.

Logic summary:
- Start from a known seed: first Thursday of the year, first owner index
- Step through Thursdays week by week
- Skip mud weeks (first 3-4 Thursdays of May each year)
- 53-Thursday years get 4 mud weeks; 52-Thursday years get 3
- Rotate through 10 owners; carry the last owner index forward year to year
- Generate from 2022 to 2100

The script should:
1. Clear existing `calendar` and `mud_weeks` rows (safe to rerun)
2. Insert all rotation rows into `calendar`
3. Insert mud week rows into `mud_weeks`

**Verification:**
- `SELECT COUNT(*) FROM calendar` — should be ~3,900 rows (10 owners × ~5 weeks/year × ~78 years from 2022)
- `SELECT COUNT(*) FROM mud_weeks` — should be ~240 rows (~3-4/year × 78 years)
- Cross-check a known year (e.g., 2025) against the "Calendar to 2100" sheet

### 2.3 Trade Detail (CSV Import)

Write `scripts/import_trade_detail.py`:

1. Read `trade_detail.csv`
2. For each row:
   - Look up `owner_id` by matching `short_name` in `owners`
   - Look up `current_holder_id` by matching the current holder name in `owners`
   - Parse `week_start` — already in MM/DD/YYYY, pass through as-is
   - Map `is_traded` (True/False text → 0/1)
   - Preserve `trade_history`, `comment`, `audit_trail`, `calculated_owner` as-is
3. Insert into `trade_detail`

**Watch out for:**
- Blank `current_holder_id` (NULL is valid — means no trade has occurred)
- Name mismatches between sheet and `owners.short_name` — log and review
- Extra whitespace in name fields from the sheet

**Verification:**
- Row count in `trade_detail` should match row count in the TradeDetail sheet (~3,900)
- Spot-check 5-10 rows with known trades against the sheet
- `SELECT COUNT(*) FROM trade_detail WHERE is_traded = 1` — compare to sheet's TradeDetailFiltered count

### 2.4 Audit (CSV Import)

Write or extend the import script for `audit.csv`:

1. Read `audit.csv`
2. Parse `timestamp` — likely a Google Sheets datetime format, convert to ISO 8601
3. Insert rows into `audit` preserving all fields

**Verification:**
- Row count should match Audit sheet (~106 rows)
- Check oldest and newest timestamps look correct

### 2.5 Site Config (Manual Entry)

Insert property info into `site_config`:

```sql
INSERT INTO site_config (key, value, note) VALUES
  ('Garage', '2071', '<neighbor name and contact — from sheet>'),
  ('WiFi', '9706683418', '<neighbor name and contact — from sheet>'),
  ('Lock Box', '4926', '<neighbor name and contact — from sheet>');
```

These values were previously hardcoded in GAS. Larry can update them via the admin table browser going forward.

### 2.6 Full Database Verification Checklist

- [ ] `owners` — 10 rows
- [ ] `owner_emails` — correct count, all emails lowercase
- [ ] `calendar` — ~3,900 rows, sample year matches sheet
- [ ] `mud_weeks` — ~240 rows, correct per-year counts
- [ ] `trade_detail` — row count matches sheet, traded rows match TradeDetailFiltered
- [ ] `audit` — row count matches sheet, timestamps look right
- [ ] `site_config` — 3 rows (Garage, WiFi, Lock Box)
- [ ] `magic_links` — 0 rows (empty, as expected)

## Scripts to Write

| Script | Purpose | Run |
|---|---|---|
| `scripts/generate_rotation.py` | Generate calendar + mud_weeks | Once, re-runnable |
| `scripts/seed_owners.py` | Insert owners + emails | Once |
| `scripts/import_trade_detail.py` | CSV → trade_detail | Once |
| `scripts/import_audit.py` | CSV → audit | Once |
| `scripts/verify_counts.py` | Print row counts for all tables | Anytime |

## Next Phase

[Phase 3 — Build Core Routes](phase-3-core-routes.md)
