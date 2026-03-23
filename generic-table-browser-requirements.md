# Generic Table Browser — Build Requirements

*A reusable Flask component that renders any SQLite table or view as a sortable, exportable HTML grid with optional CRUD — with zero per-table code.*

---

## 1. What It Does

A single Flask route takes a table name and renders it: browse rows, sort columns, export CSV, add/edit/delete. It discovers columns at runtime from SQLite metadata. No hardcoded column lists, no per-table templates, no per-table Python code.

---

## 2. Route

```
GET /admin/table/<table_name>
```

The route receives a table name, looks it up in SQLite, and renders it. How the user gets to this route (menus, links, whatever) is the app's business — the browser doesn't care.

---

## 3. Column Discovery

Use `PRAGMA table_info([<table_name>])` to discover columns at runtime. This returns column name, data type, and primary key flag. The browser renders whatever columns exist — if you `ALTER TABLE ADD COLUMN`, it appears automatically on next page load.

If `field_definitions` rows exist for this table (see Section 7), use those for display names, column ordering, and field types. If none exist, fall back to raw column names from PRAGMA and render everything as text.

---

## 4. View Detection

```sql
SELECT type FROM sqlite_master WHERE name = ?
```

If the result is `'view'` → suppress Add, Edit, and Delete. The browser becomes read-only automatically. No configuration needed.

---

## 5. Data Display

- All rows rendered in an HTML `<table>`
- Sticky column headers (`position: sticky; top: 0`)
- Alternating row colors
- Scrollable wrapper (`overflow-x: auto`) for wide tables
- Mobile responsive

---

## 6. Client-Side Sorting

- Click a column header → sort ascending. Click again → descending.
- Shift-click → add secondary/tertiary sort (up to 3 levels)
- Sort badges on headers show order and direction (e.g., "1 ▲", "2 ▼")
- Smart type detection: numbers sort numerically, dates chronologically, strings case-insensitive
- Stable sort: equal values preserve original order
- All JavaScript, no server round-trip

---

## 7. CSV Export

- "Export to CSV" button
- Server-side: query all rows, format as CSV, return as file download
- Filename: `<table_name>.csv`

---

## 8. The `h=` Report Header Convention

When the **first column** of any row starts with `h=`, render that row as a **styled section header**:

- Strip the `h=` prefix
- Bold text, spanning all columns (`colspan`)
- Distinct background color
- Remaining columns of that row are ignored

This lets SQL views embed their own section structure:

```sql
CREATE VIEW IF NOT EXISTS v_stats AS
SELECT 'h=By Region' AS label, 'Count' AS value
UNION ALL
SELECT region, CAST(COUNT(*) AS TEXT) FROM orders GROUP BY region
UNION ALL
SELECT 'h=By Status', 'Count'
UNION ALL
SELECT status, CAST(COUNT(*) AS TEXT) FROM orders GROUP BY status;
```

Two report sections with bold headers. Zero template work.

---

## 9. CRUD (Tables Only)

All CRUD is suppressed for views.

**Add:**
- "Add" button → form with one input per column
- Auto-increment primary key is hidden/auto-generated
- On submit → `INSERT INTO <table_name> (...) VALUES (...)`

**Edit:**
- "Edit" link per row → form pre-populated with current values, identified by primary key
- On submit → `UPDATE <table_name> SET ... WHERE <pk_col> = ?`

**Delete:**
- "Delete" link per row → confirmation prompt
- `DELETE FROM <table_name> WHERE <pk_col> = ?`

---

## 10. Progressive Enhancement with `field_definitions`

Optional. If this table exists and has rows for the target table, the browser uses them. If not, everything still works from PRAGMA alone.

```sql
CREATE TABLE IF NOT EXISTS field_definitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,
    column_name TEXT NOT NULL,
    display_name TEXT NOT NULL,          -- Human-friendly column header
    field_type TEXT DEFAULT 'text',      -- 'text' | 'checkbox' | 'textarea' | 'date' | 'select'
    display_order INTEGER DEFAULT 0,     -- Column sequence
    is_active INTEGER DEFAULT 1,         -- 0 = hide this column from the browser
    lov_name TEXT DEFAULT ''             -- If 'select', which LOV populates the dropdown
);
```

What it controls:
- **Column headers:** `display_name` instead of raw column names
- **Column order:** `display_order` instead of physical table order
- **Hidden columns:** `is_active = 0` suppresses a column from display and forms
- **Form field types:** checkbox, textarea, date picker instead of everything being a text input
- **Dropdowns:** `lov_name` links to `lov_values` for controlled vocabularies in edit forms

---

## 11. Progressive Enhancement with `lov_values`

Optional. Provides dropdown options for `select` fields. Supports both static rows and dynamic SQL.

```sql
CREATE TABLE IF NOT EXISTS lov_values (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lov_name TEXT NOT NULL,
    value TEXT DEFAULT '',               -- Stored value
    display_label TEXT DEFAULT '',       -- Shown in dropdown
    display_order INTEGER DEFAULT 0,
    query TEXT DEFAULT ''                -- If populated, execute this SQL instead of static rows.
                                        -- Must return two columns: value, display_label.
);
```

**Resolution logic:**
1. Find `lov_values` rows for the given `lov_name`
2. If any row has a non-empty `query` → execute it, use results as dropdown options
3. Otherwise → use static `value`/`display_label` rows ordered by `display_order`

**Static example:**
```sql
INSERT INTO lov_values (lov_name, value, display_label, display_order) VALUES
    ('STATUS_LOV', 'active', 'Active', 1),
    ('STATUS_LOV', 'inactive', 'Inactive', 2);
```

**Dynamic example:**
```sql
INSERT INTO lov_values (lov_name, query) VALUES
    ('TABLE_NAME_LOV', 'SELECT name, name FROM sqlite_master WHERE type IN (''table'', ''view'') ORDER BY name');
```

---

## 12. Key Principles

1. **No per-table code.** Columns discovered from PRAGMA. `ALTER TABLE ADD COLUMN` appears automatically.
2. **Progressive enhancement.** Works bare from PRAGMA. Add `field_definitions` for nicer labels and dropdowns. Add `lov_values` for controlled vocabularies. Each layer is optional.
3. **Views are reports.** `CREATE VIEW` + `h=` convention = formatted multi-section reports with zero template work.
4. **Convention over code.** `h=` prefix → section header. View detected → read-only. `query` column populated → dynamic dropdown.
