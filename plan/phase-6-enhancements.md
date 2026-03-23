# Phase 6 — Post-Migration Enhancements (Optional)

## Goal

Optional improvements after the migration is stable and owners are comfortable with the new app. None of these are required for launch — they're quality-of-life additions.

---

## Enhancement List

### E1 — Excel Export

**Route:** `GET /admin/export`

Generate and download an Excel file with multiple sheets (one per table or view), mimicking the familiar spreadsheet format for Larry.

```python
import openpyxl
# or: import xlsxwriter
```

Sheets to include:
- Current Year view
- Trade Detail (all active years)
- Audit log
- Owners

**Why:** Larry is comfortable with Excel. Useful for year-end review or sharing with owners outside the app.

---

### E2 — Mobile CSS Polish

Current requirement is "works on phones/tablets" — this enhancement is about making it look good, not just functional.

Options:
- [Pico CSS](https://picocss.com/) — minimal, classless, responsive out of the box
- Custom CSS tweaks for the calendar grid (wide tables are hard on small screens)

Consider a "narrow" calendar view for phones: stacked vertically instead of the wide grid, one owner per card.

---

### E3 — Automated SQLite Backup

Daily backup of `snowbound.db` to protect against accidental data loss.

Options:
- PythonAnywhere scheduled task: copy `.db` file to a timestamped backup location
- Email the `.db` file to Larry's email once a week (small file)
- Sync to Google Drive via API

Simple PythonAnywhere scheduled task (runs daily):
```bash
cp /home/<username>/snowbound/snowbound.db /home/<username>/backups/snowbound-$(date +%Y%m%d).db
# Keep last 30 days, delete older
find /home/<username>/backups/ -name "snowbound-*.db" -mtime +30 -delete
```

---

### E4 — Owner Lookup View (`/lookup`)

A second calendar view already in the route spec but deprioritized for launch.

```
GET /lookup    → pick owner + year/month range → flat list of their weeks
```

Shows: date, original owner, current holder, comments — in a simple table.

Useful for "When's my next week?" without scrolling through the full grid.

---

### E5 — Expired Magic Link Cleanup

Add a scheduled task to delete old/used/expired tokens from `magic_links`:

```sql
DELETE FROM magic_links WHERE expires_at < datetime('now', '-1 day');
```

Run daily via PythonAnywhere scheduled tasks. Keeps the table from growing indefinitely.

---

### E6 — Better Error Pages

Custom 404 and 500 pages with a link back to `/calendar`. Friendlier than Flask's default error pages for elderly users who might end up at a bad URL.

```python
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404
```

---

### E7 — Session Expiry Notice

When a session expires mid-visit, show a friendly message ("Your session has expired — please log in again") rather than a bare redirect to `/login`.

---

## Priority Order (if doing any of these)

1. **E5** (magic link cleanup) — small, automated, good hygiene
2. **E3** (backup) — protects data, low effort on PythonAnywhere
3. **E6** (error pages) — user-facing polish, quick to implement
4. **E4** (owner lookup) — already in the route spec, just needs building
5. **E1** (Excel export) — useful for Larry, moderate effort
6. **E2** (mobile CSS polish) — nice to have, lower priority if layout already works
7. **E7** (session expiry notice) — minor UX improvement
