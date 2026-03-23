# Phase 5 — Deploy & Cutover

## Goal

Deploy the locally-tested Flask app to PythonAnywhere, do a final data sync, send the new URL to all owners, and keep the old GAS app alive in read-only mode for 30 days as a fallback.

## Prerequisites

- Phase 4 complete (all tests pass, Larry signed off on local version)
- No open issues from the testing phase

## Notes from Phase 4

- **9 owners, not 10.** Database has 9 active owners (IDs 1–9). Loyle is counted once despite being two families.
- **"Give Away" is comment-only.** Does not transfer `current_holder_id`. If transferring ownership is needed, use "Trade Week" instead. Confirm this behavior is acceptable before cutover.
- **Previous/Next year links go relative to today, not the viewed year.** By design — use the year picker dropdown to navigate non-current years.
- **SMTP not tested locally.** Magic links appeared as flash messages during Phase 4 dev testing. SMTP must be configured and verified on PythonAnywhere before announcing to owners (Step 1.3 + Step 5).
- **Reseed scripts run order matters.** Must run in this sequence: `seed_owners` → `generate_rotation` → `import_trade_detail` → `import_audit` → `verify_counts`. On PythonAnywhere the scripts path is `snowbound/scripts/`, not `scripts/` directly.
- **No virtual environment in local dev.** Packages were installed globally (Python 3.14). On PythonAnywhere, use a proper virtualenv as documented in Step 1.3.
- **DB path uses 4 slashes on PythonAnywhere.** `DATABASE_URL=sqlite:////home/<username>/snowbound/snowbound.db` — the extra slash makes it an absolute path.

---

## Step 1 — PythonAnywhere Setup

### 1.1 Create Account

- [ ] Create PythonAnywhere account at pythonanywhere.com
- [ ] Free tier to start — upgrade to $5/month if:
  - SMTP for magic links is blocked (free tier restricts outbound email)
  - Custom domain (`69hawn.com` or `calendar.69hawn.com`) is desired

### 1.2 Upload the App

Options (pick one):
- **Git:** Push to a GitHub repo, then `git clone` from the PythonAnywhere bash console
- **Upload:** Use the PythonAnywhere Files tab to upload the project folder
- **rsync/scp:** If comfortable with SSH (PythonAnywhere provides SSH on paid tier)

Do **not** upload:
- `.env` (create it fresh on the server — see 1.3)
- `snowbound.db` (will be created fresh in step 3)
- `.venv` (recreate on the server)

### 1.3 Server Environment

In the PythonAnywhere bash console:

```bash
# Create virtualenv
python3 -m venv ~/.venvs/snowbound
source ~/.venvs/snowbound/bin/activate
pip install -r requirements.txt

# Create .env with production values
nano /home/<username>/snowbound/.env
```

Production `.env` values to set:
- `SECRET_KEY` — generate a new random string (different from local)
- `DATABASE_URL=sqlite:////home/<username>/snowbound/snowbound.db`  (4 slashes = absolute path)
- SMTP credentials for magic links
- `ADMIN_EMAIL=larry@kamons.com`

### 1.4 Configure the Web App

In the PythonAnywhere Web tab:
- [ ] Create a new web app → Manual configuration → Python 3.x
- [ ] Set **Source code** path to `/home/<username>/snowbound`
- [ ] Set **Virtualenv** path to `/home/.venvs/snowbound`
- [ ] Edit the **WSGI file** to point at your Flask app:
  ```python
  import sys
  sys.path.insert(0, '/home/<username>/snowbound')
  from app import app as application
  ```
- [ ] Reload the web app
- [ ] Confirm the `.pythonanywhere.com` URL loads the placeholder page

---

## Step 2 — Seed Production Database

Run the same scripts used locally, now on the server:

```bash
cd /home/<username>/snowbound
source ~/.venvs/snowbound/bin/activate
python scripts/seed_owners.py
python scripts/generate_rotation.py
python scripts/import_trade_detail.py   # using the latest CSV exports
python scripts/import_audit.py
python scripts/verify_counts.py
```

Verify row counts match local database.

---

## Step 3 — Freeze the GAS App (Soft)

Notify Larry: "Don't submit any new trades in the Google app during the final sync window." Duration: a few hours, ideally early morning.

---

## Step 4 — Final Data Sync

1. Export `TradeDetail` sheet to CSV one last time
2. Export `Audit` sheet to CSV one last time
3. Upload CSVs to PythonAnywhere, re-run import scripts (truncate + reload)
4. Run `verify_counts.py` — confirm all row counts match
5. Verify the most recent trade in the sheet appears correctly in the Flask app

---

## Step 5 — Final Smoke Test on Production

- [ ] `/calendar` shows current year correctly at the PythonAnywhere URL
- [ ] Latest trade comments visible
- [ ] Larry logs in via magic link (confirms SMTP is working)
- [ ] Submit a test "Comment" trade → appears in database and calendar
- [ ] Delete the test trade via admin table browser

---

## Step 6 — Announce to Owners

Send an email to all owners (use the `/email` compose page on the new app!) with:

- The new URL
- Brief instructions — no Google account needed
- How to log in: enter your email, click the link you receive
- Note: the old Google app will still be readable for 30 days

Tone: simple and reassuring. "Same information, easier to use, works on your phone."

---

## Step 7 — Make GAS App Read-Only

In Google Apps Script:
- Comment out or remove the `doPost()` handler in `Code.js`
- Redeploy the web app
- Optionally add a banner to `Form.html`: "This form has moved to [new URL]. This version is read-only."

---

## Step 8 — Monitor

For the first week after cutover:
- [ ] Magic links are being sent and received
- [ ] Review `/admin/table/audit` for new submissions
- [ ] Watch PythonAnywhere error logs for any exceptions

---

## Rollback Plan

If a critical issue emerges:
1. Direct users back to the old GAS app URL (still live, read-only)
2. No data divergence to worry about (GAS is read-only)
3. Fix the issue locally, re-deploy, re-cutover

---

## 30-Day Overlap Period

- Keep GAS app live but read-only for 30 days
- After 30 days with no issues, decommission:
  - Disable `doGet` in the GAS app or return a redirect message
  - Keep the Google Sheet as a read-only historical archive

---

## Decommission Checklist (After 30 Days)

- [ ] No owner-reported issues in the last 30 days
- [ ] GAS app disabled
- [ ] Google Sheet retained as read-only archive
- [ ] Note added to the sheet that the live app has moved

---

## Post-Cutover

Once stable, consider [Phase 6 — Post-Migration Enhancements](phase-6-enhancements.md).
