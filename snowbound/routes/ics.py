from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, Response, flash, redirect, url_for
from icalendar import Calendar as ICalendar, Event
from .. import db
from ..models import Owner, TradeDetail

bp = Blueprint("ics", __name__)


@bp.route("/ics")
def ics_form():
    owners = Owner.query.filter_by(is_active=True).order_by(Owner.short_name).all()
    return render_template("ics.html", owners=owners, year_range=range(2022, 2101))


@bp.route("/ics/download", methods=["POST"])
def ics_download():
    owner_id = request.form.get("owner_id", type=int)
    year = request.form.get("year", type=int)

    if not owner_id or not year:
        flash("Owner and year are required.", "error")
        return redirect(url_for("ics.ics_form"))

    owner = Owner.query.get(owner_id)
    if not owner:
        flash("Owner not found.", "error")
        return redirect(url_for("ics.ics_form"))

    trades = (TradeDetail.query
              .filter_by(year=year, owner_id=owner_id)
              .order_by(TradeDetail.week_start)
              .all())

    cal = ICalendar()
    cal.add("prodid", "-//Snowbound LLC//Condo Calendar//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("x-wr-calname", f"Snowbound {owner.short_name} {year}")

    for t in trades:
        start = datetime.strptime(t.week_start, "%m/%d/%Y").date()
        end = start + timedelta(days=7)  # exclusive end for all-day events

        holder = t.calculated_owner or owner.short_name
        summary = f"69hawn.com - {holder}"

        event = Event()
        event.add("summary", summary)
        event.add("dtstart", start)
        event.add("dtend", end)
        if t.comment:
            event.add("description", t.comment)
        event.add("uid", f"{t.week_start.replace('/', '')}-{owner_id}@69hawn.com")
        cal.add_component(event)

    filename = f"snowbound_{owner.short_name.lower()}_{year}.ics"
    return Response(
        cal.to_ical(),
        mimetype="text/calendar",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
