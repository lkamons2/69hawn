import csv
import io
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from sqlalchemy import text
from .. import db
from ..decorators import admin_required

bp = Blueprint("admin", __name__, url_prefix="/admin")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _table_type(name):
    """Return 'table', 'view', or None."""
    row = db.session.execute(
        text("SELECT type FROM sqlite_master WHERE name = :n"),
        {"n": name},
    ).fetchone()
    return row[0] if row else None


def _pragma_cols(name):
    """Return list of dicts from PRAGMA table_info."""
    rows = db.session.execute(text(f"PRAGMA table_info([{name}])")).fetchall()
    return [
        {"name": r[1], "type": r[2], "notnull": bool(r[3]), "pk": r[5] > 0}
        for r in rows
    ]


def _field_defs(name):
    rows = db.session.execute(
        text(
            "SELECT column_name, display_name, field_type, display_order, is_active, lov_name "
            "FROM field_definitions WHERE table_name = :t ORDER BY display_order"
        ),
        {"t": name},
    ).fetchall()
    return [
        {
            "column_name": r[0],
            "display_name": r[1],
            "field_type": r[2],
            "display_order": r[3],
            "is_active": r[4],
            "lov_name": r[5] or "",
        }
        for r in rows
    ]


def _lov_options(lov_name):
    if not lov_name:
        return []
    rows = db.session.execute(
        text(
            "SELECT value, display_label, query FROM lov_values "
            "WHERE lov_name = :n ORDER BY display_order"
        ),
        {"n": lov_name},
    ).fetchall()
    # If any row has a SQL query, execute it instead
    for r in rows:
        if r[2]:
            result = db.session.execute(text(r[2])).fetchall()
            return [{"value": str(row[0]), "label": str(row[1])} for row in result]
    return [{"value": r[0] or "", "label": r[1] or r[0] or ""} for r in rows]


def _existing_table_names():
    rows = db.session.execute(
        text("SELECT name FROM sqlite_master WHERE type='table'")
    ).fetchall()
    return {r[0] for r in rows}


def _fk_overrides_map():
    """Return {(table_name, column_name): ref_table} from fk_overrides."""
    try:
        rows = db.session.execute(
            text("SELECT table_name, column_name, ref_table FROM fk_overrides")
        ).fetchall()
        return {(r[0], r[1]): r[2] for r in rows}
    except Exception:
        return {}


def _fk_table_for(table_name, col_name, existing_tables, overrides):
    """Return the referenced table name for a FK column, or ''."""
    # Explicit override wins
    override = overrides.get((table_name, col_name))
    if override:
        return override
    # Convention: foo_id -> foos or foo
    if col_name == "id" or not col_name.endswith("_id"):
        return ""
    stem = col_name[:-3]
    for candidate in (stem + "s", stem):
        if candidate in existing_tables:
            return candidate
    return ""


def _build_cols(table_name, pragma):
    """Merge PRAGMA columns with field_definitions enhancements."""
    existing_tables = _existing_table_names()
    overrides = _fk_overrides_map()
    fd_list = _field_defs(table_name)
    if not fd_list:
        return [
            {
                "name": c["name"],
                "display_name": c["name"].replace("_", " ").title(),
                "field_type": "text",
                "is_active": 1,
                "pk": c["pk"],
                "lov_options": [],
                "fk_table": _fk_table_for(table_name, c["name"], existing_tables, overrides),
            }
            for c in pragma
        ]

    fd_map = {fd["column_name"]: fd for fd in fd_list}
    cols = []
    for c in pragma:
        fd = fd_map.get(c["name"])
        if fd:
            if not fd["is_active"]:
                continue
            lov = _lov_options(fd["lov_name"]) if fd["field_type"] == "select" else []
            cols.append(
                {
                    "name": c["name"],
                    "display_name": fd["display_name"],
                    "field_type": fd["field_type"],
                    "is_active": 1,
                    "pk": c["pk"],
                    "lov_options": lov,
                    "fk_table": _fk_table_for(table_name, c["name"], existing_tables, overrides),
                }
            )
        else:
            cols.append(
                {
                    "name": c["name"],
                    "display_name": c["name"].replace("_", " ").title(),
                    "field_type": "text",
                    "is_active": 1,
                    "pk": c["pk"],
                    "lov_options": [],
                    "fk_table": _fk_table_for(table_name, c["name"], existing_tables, overrides),
                }
            )
    return cols


def _all_tables():
    rows = db.session.execute(
        text(
            "SELECT name, type FROM sqlite_master "
            "WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' "
            "ORDER BY type DESC, name"
        )
    ).fetchall()
    return rows


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@bp.route("/")
@admin_required
def index():
    tables = _all_tables()
    return render_template("admin/index.html", tables=tables)


@bp.route("/table/<name>")
@admin_required
def table(name):
    ttype = _table_type(name)
    if not ttype:
        flash(f"Table or view '{name}' not found.", "error")
        return redirect(url_for("admin.index"))

    is_view = ttype == "view"
    pragma = _pragma_cols(name)
    columns = _build_cols(name, pragma)
    pk_col = next((c["name"] for c in columns if c["pk"]), None)

    # Build WHERE clause from URL params that match actual column names
    valid_cols = {c["name"] for c in columns}
    filters = {k: v for k, v in request.args.items() if k in valid_cols and v != ""}
    if filters:
        where = " AND ".join(f"[{k}] LIKE :{k}" for k in filters)
        rows = db.session.execute(
            text(f"SELECT * FROM [{name}] WHERE {where}"), filters
        ).fetchall()
    else:
        rows = db.session.execute(text(f"SELECT * FROM [{name}]")).fetchall()

    return render_template(
        "admin/table.html",
        table_name=name,
        columns=columns,
        rows=rows,
        is_view=is_view,
        pk_col=pk_col,
        all_tables=_all_tables(),
        filters=filters,
    )


@bp.route("/table/<name>/add", methods=["POST"])
@admin_required
def add_row(name):
    pragma = _pragma_cols(name)
    columns = _build_cols(name, pragma)
    insert_cols = [c for c in columns if not c["pk"]]

    if not insert_cols:
        flash("Nothing to insert.", "error")
        return redirect(url_for("admin.table", name=name))

    col_list = ", ".join(f"[{c['name']}]" for c in insert_cols)
    placeholders = ", ".join(f":{c['name']}" for c in insert_cols)
    params = {}
    for c in insert_cols:
        val = request.form.get(c["name"], "")
        if c["field_type"] == "checkbox":
            val = "1" if val == "on" else "0"
        params[c["name"]] = val or None

    db.session.execute(
        text(f"INSERT INTO [{name}] ({col_list}) VALUES ({placeholders})"),
        params,
    )
    db.session.commit()
    flash("Row added.", "info")
    return redirect(url_for("admin.table", name=name))


@bp.route("/table/<name>/edit/<pk_val>", methods=["GET", "POST"])
@admin_required
def edit_row(name, pk_val):
    pragma = _pragma_cols(name)
    columns = _build_cols(name, pragma)
    pk_col = next((c["name"] for c in columns if c["pk"]), "id")
    non_pk = [c for c in columns if not c["pk"]]

    if request.method == "POST":
        set_clause = ", ".join(f"[{c['name']}] = :{c['name']}" for c in non_pk)
        params = {}
        for c in non_pk:
            val = request.form.get(c["name"], "")
            if c["field_type"] == "checkbox":
                val = "1" if val == "on" else "0"
            params[c["name"]] = val or None
        params["_pk_val"] = pk_val

        db.session.execute(
            text(f"UPDATE [{name}] SET {set_clause} WHERE [{pk_col}] = :_pk_val"),
            params,
        )
        db.session.commit()
        flash("Row updated.", "info")
        return redirect(url_for("admin.table", name=name))

    row = db.session.execute(
        text(f"SELECT * FROM [{name}] WHERE [{pk_col}] = :pk"),
        {"pk": pk_val},
    ).fetchone()

    if not row:
        flash("Row not found.", "error")
        return redirect(url_for("admin.table", name=name))

    # Build a dict for the template
    pragma_names = [c["name"] for c in pragma]
    row_dict = dict(zip(pragma_names, row))

    return render_template(
        "admin/edit.html",
        table_name=name,
        columns=columns,
        row_dict=row_dict,
        pk_col=pk_col,
        pk_val=pk_val,
        is_add=False,
    )


@bp.route("/table/<name>/add_form", methods=["GET"])
@admin_required
def add_form(name):
    pragma = _pragma_cols(name)
    columns = _build_cols(name, pragma)
    pk_col = next((c["name"] for c in columns if c["pk"]), "id")

    return render_template(
        "admin/edit.html",
        table_name=name,
        columns=columns,
        row_dict={},
        pk_col=pk_col,
        pk_val=None,
        is_add=True,
    )


@bp.route("/table/<name>/delete/<pk_val>", methods=["POST"])
@admin_required
def delete_row(name, pk_val):
    pragma = _pragma_cols(name)
    columns = _build_cols(name, pragma)
    pk_col = next((c["name"] for c in columns if c["pk"]), "id")

    db.session.execute(
        text(f"DELETE FROM [{name}] WHERE [{pk_col}] = :pk"),
        {"pk": pk_val},
    )
    db.session.commit()
    flash("Row deleted.", "info")
    return redirect(url_for("admin.table", name=name))


@bp.route("/table/<name>/export.csv")
@admin_required
def export_csv(name):
    pragma = _pragma_cols(name)
    col_names = [c["name"] for c in pragma]
    rows = db.session.execute(text(f"SELECT * FROM [{name}]")).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(col_names)
    for row in rows:
        writer.writerow([v if v is not None else "" for v in row])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={name}.csv"},
    )


@bp.route("/export")
@admin_required
def export():
    return redirect(url_for("admin.index"))
