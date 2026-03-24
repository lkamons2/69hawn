from datetime import date, datetime, timedelta
from collections import defaultdict
from flask import Blueprint, render_template, redirect, url_for, request
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

    owner_trades = defaultdict(list)
    for t in trades:
        owner_trades[t.owner_id].append(t)

    # Sort owners by their earliest week_start in this year (chronological rotation order)
    def owner_first_week(owner):
        weeks = owner_trades.get(owner.id, [])
        if weeks:
            d = datetime.strptime(weeks[0].week_start, "%m/%d/%Y")
            return d
        return datetime.max

    owners = sorted(owners, key=owner_first_week)

    rows = []
    max_weeks = 5
    for owner in owners:
        week_cells = {}
        for t in owner_trades.get(owner.id, []):
            wn = week_num_map.get((t.owner_id, t.week_start), len(week_cells) + 1)
            week_cells[wn] = {
                "week_start": t.week_start,
                "week_end": _week_end(t.week_start),
                "is_traded": bool(t.is_traded),
                "current_owner": t.calculated_owner or owner.short_name,
                "original_owner": owner.short_name,
                "comment": t.comment or "",
            }
        if week_cells:
            max_weeks = max(max_weeks, max(week_cells.keys()))
        cells = [week_cells.get(n) for n in range(1, max_weeks + 1)]
        rows.append({"owner": owner, "cells": cells})

    # Pad all rows to same length
    for row in rows:
        while len(row["cells"]) < max_weeks:
            row["cells"].append(None)

    return render_template(
        "calendar.html",
        year=year,
        rows=rows,
        configs=configs,
        prev_year=year - 1,
        next_year=year + 1,
        year_range=range(2022, 2101),
        max_weeks=max_weeks,
    )


@bp.route("/lookup")
@login_required
def lookup():
    owners = Owner.query.filter_by(is_active=True).order_by(Owner.short_name).all()
    owner_id = request.args.get("owner_id", type=int)
    year = request.args.get("year", type=int, default=date.today().year)

    weeks = []
    if owner_id is not None:
        q = TradeDetail.query.filter_by(year=year)
        if owner_id != 0:
            q = q.filter_by(owner_id=owner_id)
        for t in q.order_by(TradeDetail.week_start).all():
            weeks.append({
                "week_start": t.week_start,
                "week_end": _week_end(t.week_start),
                "original_owner": t.owner.short_name,
                "current_owner": t.calculated_owner or t.owner.short_name,
                "is_traded": bool(t.is_traded),
                "comment": t.comment or "",
            })

    return render_template(
        "lookup.html",
        owners=owners,
        weeks=weeks,
        selected_owner_id=owner_id,
        selected_year=year,
        year_range=range(2022, 2101),
    )
