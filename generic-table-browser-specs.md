# Generic Table Browser — Specification (As Built)

*A reusable Flask + SQLite component that renders any table or view as a sortable, exportable HTML grid with optional CRUD — with zero per-table code.*

---

## 1. What It Does

A small set of Flask routes and two Jinja2 templates handle every table and view in a SQLite database. Browse rows, sort columns, export CSV, add/edit/delete. Columns are discovered at runtime from SQLite metadata. No hardcoded column lists, no per-table templates, no per-table Python code.

---

## 2. Routes

| Method | Route | Purpose |
|---|---|---|
| GET | `/admin/` | Index page — lists all tables and views |
| GET | `/admin/table/<name>` | Browse a table or view |
| GET | `/admin/table/<name>/add_form` | Blank add form |
| POST | `/admin/table/<name>/add` | Insert new row |
| GET | `/admin/table/<name>/edit/<pk_val>` | Pre-populated edit form |
| POST | `/admin/table/<name>/edit/<pk_val>` | Update existing row |
| POST | `/admin/table/<name>/delete/<pk_val>` | Delete a row (with JS confirmation) |
| GET | `/admin/table/<name>/export.csv` | Download all rows as CSV |

All routes are protected by an `@admin_required` decorator.

---

## 3. Index Page

`GET /admin/` renders two lists:
- **Tables** — full CRUD available
- **Views (read-only)** — browse and export only

Each item is a link to `/admin/table/<name>`.

---

## 4. Column Discovery

```python
PRAGMA table_info([<table_name>])
```

Returns column name, data type, not-null flag, and primary key flag. The browser renders whatever columns exist — if you `ALTER TABLE ADD COLUMN`, it appears automatically on next page load with no code changes.

If `field_definitions` rows exist for this table (see Section 13), they override display names, ordering, and field types. If not, the browser falls back to raw PRAGMA data and renders everything as plain text with title-cased headers.

---

## 5. View Detection

```sql
SELECT type FROM sqlite_master WHERE name = ?
```

If the result is `'view'` → Add, Edit, and Delete are suppressed. The table browser becomes read-only automatically. The page heading shows a small `(view)` label. No configuration needed.

---

## 6. Data Display

- All rows in an HTML `<table>` with `id="adminTable"`
- Scrollable wrapper (`overflow-x: auto`) for wide tables
- Row count displayed next to the action buttons
- `+ Add Row` button shown for tables, hidden for views
- `Export CSV` button shown for all
- Checkbox columns render as ✓ or blank (not 0/1)
- FK columns render as hyperlinks (see Section 12)

---

## 7. Filter Bar

Every table/view page renders a filter bar above the data grid. One text input per column, plus a **Filter** button.

- Filters are passed as URL query parameters: `?year=2026&is_traded=1`
- Only parameters matching actual column names are applied (others ignored)
- Empty inputs are excluded from the filter
- Server-side: builds a `WHERE col = :val AND ...` clause using parameterized queries
- Exact match only (no wildcards or LIKE)
- A **Clear Filters** button appears when any filter is active, linking back to the unfiltered table
- Bookmarkable: since filters are URL params, filtered views can be shared or bookmarked directly

---

## 8. Client-Side Sorting

- Click a column header → sort ascending. Click again → descending.
- **Shift-click** → add secondary/tertiary sort key (up to 3 levels)
- Sort badges on headers show priority and direction: `1 ▲`, `2 ▼`, `3 ▲`
- Section header rows (see Section 9) are excluded from sorting
- All JavaScript, no server round-trip

**Smart type detection** (in priority order):

1. **Date/datetime** — checked first to prevent datetime strings being mis-parsed as numbers
   - `MM/DD/YYYY` — parsed as local date
   - `YYYY-MM-DD HH:MM:SS` or `YYYY-MM-DD HH:MM:SS.ffffff` (SQLite datetime) — any whitespace between date and time parts (including newlines from multi-line cell rendering) is normalized to `T` before parsing
2. **Numeric** — `parseFloat` on the cell text; both values must be numeric
3. **String** — case-insensitive `localeCompare`

Stable sort: equal values preserve original DB order.

---

## 9. The `h=` Report Header Convention

When the **first column** of any row starts with `h=`, that row renders as a **styled section header**:

- `h=` prefix is stripped
- Bold text spanning all columns (`colspan`)
- Distinct background color (`#d0e4f7`)
- Not sortable (excluded from sort operations)
- Remaining columns of that row are ignored

This lets SQL views embed their own section structure with no template changes:

```sql
CREATE VIEW v_report AS
SELECT 'h=Active Owners' AS label, '' AS detail
UNION ALL
SELECT short_name, full_name FROM owners WHERE is_active = 1
UNION ALL
SELECT 'h=Inactive Owners', ''
UNION ALL
SELECT short_name, full_name FROM owners WHERE is_active = 0;
```

---

## 10. CRUD

All write operations are suppressed for views.

**Add:**
- `+ Add Row` link → blank form (`add_form` route)
- Auto-increment primary key is hidden; all other non-PK columns shown
- On submit → `POST /admin/table/<name>/add` → `INSERT INTO [<name>] (...) VALUES (...)`
- Redirects back to the table browser on success

**Edit:**
- `Edit` link per row → pre-populated form (`edit_row` GET)
- Primary key shown as a disabled read-only field
- On submit → `POST /admin/table/<name>/edit/<pk_val>` → `UPDATE [<name>] SET ... WHERE [<pk_col>] = ?`
- Redirects back to the table browser on success

**Delete:**
- `Del` button per row → JavaScript `confirm()` dialog
- On confirm → `POST /admin/table/<name>/delete/<pk_val>` → `DELETE FROM [<name>] WHERE [<pk_col>] = ?`
- Redirects back to the table browser on success

---

## 11. CSV Export

- `Export CSV` button → `GET /admin/table/<name>/export.csv`
- Server-side: queries all rows, streams as CSV file download
- Column headers are raw column names from PRAGMA (not display names)
- Filename: `<table_name>.csv`
- `None` values rendered as empty string

---

## 12. Foreign Key Auto-Linking

FK columns in the table browser render their values as hyperlinks to the edit page of the referenced row. Resolution uses two mechanisms:

### 12a. Convention-based (automatic)

Any column named `<stem>_id` (but not plain `id`) is automatically detected as a FK. The browser tries to find the referenced table by:
1. `<stem>s` (e.g., `owner_id` → `owners`)
2. `<stem>` (e.g., `owner_id` → `owner`)

If a matching table exists in `sqlite_master`, the cell value becomes a link to `/admin/table/<ref_table>/edit/<value>`.

### 12b. `fk_overrides` table (explicit metadata)

For columns where naming convention doesn't resolve (e.g., `current_holder_id` → `owners`), add a row to `fk_overrides`. Explicit overrides always win over convention.

```sql
CREATE TABLE fk_overrides (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name  TEXT NOT NULL,   -- table containing the FK column
    column_name TEXT NOT NULL,   -- the FK column name
    ref_table   TEXT NOT NULL    -- table it points to
);
```

Example:
```sql
INSERT INTO fk_overrides (table_name, column_name, ref_table)
VALUES ('trade_detail', 'current_holder_id', 'owners');
```

The `fk_overrides` table is seeded at app startup for all known non-conventional FKs, so it survives database reloads during testing.

**Resolution order:**
1. Check `fk_overrides` for an explicit entry → use `ref_table`
2. Try convention (`<stem>s`, then `<stem>`) against `sqlite_master` tables
3. No match → render as plain text

---

## 13. Progressive Enhancement with `field_definitions`

Optional. If this table exists and has rows for the target table, the browser uses them. If not, everything still works from PRAGMA alone.

```sql
CREATE TABLE field_definitions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name   TEXT NOT NULL,
    column_name  TEXT NOT NULL,
    display_name TEXT NOT NULL,         -- Human-friendly column header
    field_type   TEXT DEFAULT 'text',   -- text | checkbox | textarea | date | select
    display_order INTEGER DEFAULT 0,   -- Column sequence in the browser
    is_active    INTEGER DEFAULT 1,    -- 0 = hide this column entirely
    lov_name     TEXT DEFAULT ''        -- If 'select', which LOV populates the dropdown
);
```

**What it controls:**

| Setting | Effect |
|---|---|
| `display_name` | Column header shown instead of raw column name |
| `display_order` | Column sequence overrides physical table order |
| `is_active = 0` | Column hidden from both the table view and edit forms |
| `field_type = 'checkbox'` | Renders as ✓/blank in browse, checkbox in edit form |
| `field_type = 'textarea'` | Edit form renders a multi-line textarea |
| `field_type = 'date'` | Edit form shows a text input with `MM/DD/YYYY` placeholder |
| `field_type = 'select'` | Edit form shows a dropdown populated from `lov_values` |

Columns not listed in `field_definitions` still appear as plain text with auto-generated title-cased headers, unless `field_definitions` rows exist for the table (in which case only listed columns appear).

---

## 14. Progressive Enhancement with `lov_values`

Optional. Provides dropdown options for `select` fields. Supports static rows and dynamic SQL queries.

```sql
CREATE TABLE lov_values (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    lov_name      TEXT NOT NULL,
    value         TEXT DEFAULT '',         -- Stored value
    display_label TEXT DEFAULT '',         -- Shown in dropdown
    display_order INTEGER DEFAULT 0,
    query         TEXT DEFAULT ''          -- If populated, execute this SQL instead of static rows.
                                           -- Must SELECT two columns: value, display_label.
);
```

**Resolution logic:**
1. Find `lov_values` rows for the given `lov_name`
2. If any row has a non-empty `query` → execute it, use results as dropdown options
3. Otherwise → use static `value`/`display_label` rows ordered by `display_order`

**Static example:**
```sql
INSERT INTO lov_values (lov_name, value, display_label, display_order) VALUES
    ('TRADE_TYPE_LOV', 'Trade Week',  'Trade Week',  1),
    ('TRADE_TYPE_LOV', 'Give Away',   'Give Away',   2),
    ('TRADE_TYPE_LOV', 'Not Using',   'Not Using',   3),
    ('TRADE_TYPE_LOV', 'Comment',     'Comment',     4);
```

**Dynamic example (self-referencing — dropdown from a live table):**
```sql
INSERT INTO lov_values (lov_name, query) VALUES
    ('OWNER_LOV', 'SELECT id, short_name FROM owners WHERE is_active=1 ORDER BY short_name');
```

---

## 15. Database Requirements

The browser needs no tables of its own to function. The supporting tables are all optional and additive:

| Table | Required? | Purpose |
|---|---|---|
| `field_definitions` | Optional | Display names, ordering, field types, hidden columns |
| `lov_values` | Optional | Dropdown options for `select` fields |
| `fk_overrides` | Optional | Explicit FK → table mappings for non-conventional column names |

---

## 16. Key Design Principles

1. **No per-table code.** Columns discovered from PRAGMA. `ALTER TABLE ADD COLUMN` appears automatically.
2. **Progressive enhancement.** Works bare from PRAGMA alone. Add `field_definitions` for nicer labels and form types. Add `lov_values` for controlled vocabularies. Add `fk_overrides` for explicit FK links. Each layer is optional and additive.
3. **Views are reports.** `CREATE VIEW` + `h=` convention = formatted multi-section reports with zero template work.
4. **Convention over code.** `h=` prefix → section header. View detected → read-only. `query` column populated → dynamic dropdown. `*_id` column → auto-linked FK.
5. **Overrides over convention.** When naming convention is ambiguous or wrong, `fk_overrides` provides an explicit metadata-driven escape hatch — no code changes needed.
6. **Sort correctness.** Date/datetime detection runs before numeric detection to prevent ISO datetime strings from being partially parsed as numbers.
