from datetime import date, datetime, timedelta
from collections import defaultdict
from flask import Blueprint, render_template, redirect, url_for, request
from sqlalchemy import text
from .. import db
from ..models import Calendar, TradeDetail, Owner, SiteConfig
from ..decorators import login_required

bp = Blueprint("calendar", __name__)


def _week_end(week_start_str):
    d = datetime.strptime(week_start_str, "%m/%d/%Y")
    return (d + timedelta(days=6)).strftime("%m/%d/%Y")


@bp.route("/")
@login_required
def index():
    return redirect(url_for("calendar.year_view", year=date.today().year))


@bp.route("/calendar")
@login_required
def current():
    return redirect(url_for("calendar.year_view", year=date.today().year))


@bp.route("/calendar/prev")
@login_required
def prev():
    return redirect(url_for("calendar.year_view", year=date.today().year - 1))


@bp.route("/calendar/next")
@login_required
def next_year():
    return redirect(url_for("calendar.year_view", year=date.today().year + 1))


@bp.route("/calendar/<int:year>")
@login_required
def year_view(year):
    configs = {sc.key: sc for sc in SiteConfig.query.all()}
    owners = Owner.query.filter_by(is_active=True).all()

    # week_number map: (owner_id, week_start) -> week_number
    cal_weeks = Calendar.query.filter_by(year=year).all()
    week_num_map = {(c.owner_id, c.week_start): c.week_number for c in cal_weeks}

    # trade_detail for the year
    trades = (TradeDetail.query
              .filter_by(year=year)
              .order_by(TradeDetail.week_start)
              .all())

    owner_map = {o.id: o for o in owners}

    owner_trades = defaultdict(list)
    for t in trades:
        owner_trades[t.owner_id].append(t)

    # Build rotation slots: each slot is a row of up to 5 weeks.
    # For most owners there is one slot (wn 1-5). Loyle has two
    # rotation positions so she gets two slots (wn 1-5 and wn 6-10).
    # Slots are sorted independently by their first week_start so
    # Loyle's two slots appear in their correct rotation positions
    # rather than being grouped together.
    WEEKS_PER_ROW = 5
    slots = []  # list of (first_week_start, owner, cells_dict, slot_index)

    for owner in owners:
        all_cells = {}
        for t in owner_trades.get(owner.id, []):
            wn = week_num_map.get((t.owner_id, t.week_start), len(all_cells) + 1)
            all_cells[wn] = {
                "week_start": t.week_start,
                "week_end": _week_end(t.week_start),
                "is_traded": bool(t.is_traded),
                "current_owner": t.calculated_owner or owner.name,
                "original_owner": owner.name,
                "comment": t.comment or "",
            }

        max_wn = max(all_cells.keys()) if all_cells else 0
        num_rows = max(1, (max_wn + WEEKS_PER_ROW - 1) // WEEKS_PER_ROW)
        for row_idx in range(num_rows):
            start = row_idx * WEEKS_PER_ROW + 1
            cells = [all_cells.get(start + i) for i in range(WEEKS_PER_ROW)]
            # First non-empty cell's week_start determines sort position
            first_ws = next((c["week_start"] for c in cells if c), None)
            first_dt = datetime.strptime(first_ws, "%m/%d/%Y") if first_ws else datetime.max
            slots.append((first_dt, owner, cells, row_idx))

    # Sort all slots chronologically by their first week_start
    slots.sort(key=lambda s: s[0])

    # Track which owners have already had their info row shown
    owner_info_shown = set()
    rows = []
    for _, owner, cells, row_idx in slots:
        show_info = owner.id not in owner_info_shown
        owner_info_shown.add(owner.id)
        rows.append({
            "owner": owner,
            "cells": cells,
            "show_owner_info": show_info,
        })

    return render_template(
        "calendar.html",
        year=year,
        rows=rows,
        configs=configs,
        prev_year=year - 1,
        next_year=year + 1,
        year_range=range(2022, 2101),
    )


@bp.route("/lookup")
@login_required
def lookup():
    owners = Owner.query.filter_by(is_active=True).order_by(Owner.name).all()
    owner_ids = request.args.getlist("owner_id", type=int)
    year = request.args.get("year", type=int, default=date.today().year)
    search_by = request.args.get("search_by", "owner")

    # 0 means "All Owners"
    select_all = 0 in owner_ids

    weeks = []
    if owner_ids:
        q = TradeDetail.query.filter_by(year=year)
        if not select_all:
            if search_by == "holder":
                # Weeks they currently hold: traded TO them, or their own untraded weeks
                q = q.filter(db.or_(
                    TradeDetail.current_holder_id.in_(owner_ids),
                    db.and_(
                        TradeDetail.owner_id.in_(owner_ids),
                        TradeDetail.current_holder_id.is_(None),
                    ),
                ))
            else:
                q = q.filter(TradeDetail.owner_id.in_(owner_ids))
        for t in q.order_by(TradeDetail.week_start).all():
            weeks.append({
                "week_start": t.week_start,
                "week_end": _week_end(t.week_start),
                "original_owner": t.owner.name,
                "current_owner": t.calculated_owner or t.owner.name,
                "is_traded": bool(t.is_traded),
                "comment": t.comment or "",
            })

    return render_template(
        "lookup.html",
        owners=owners,
        weeks=weeks,
        selected_owner_ids=owner_ids,
        selected_year=year,
        selected_search_by=search_by,
        year_range=range(2022, 2101),
    )


@bp.route("/directory")
@login_required
def directory():
    rows = db.session.execute(text("SELECT * FROM v_directory")).fetchall()
    columns = ["Owner", "Name", "Phone", "Email", "Notes"]
    return render_template("directory.html", rows=rows, columns=columns)
