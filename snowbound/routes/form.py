import json
from datetime import date, datetime
from collections import defaultdict
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from .. import db
from ..models import Owner, TradeDetail, Audit
from ..decorators import login_required

bp = Blueprint("form", __name__)


@bp.route("/form", methods=["GET", "POST"])
@login_required
def form():
    owners = Owner.query.filter_by(is_active=True).order_by(Owner.short_name).all()

    today_year = date.today().year
    trades_by_owner = defaultdict(list)
    for yr in range(today_year - 1, today_year + 4):
        rows = (TradeDetail.query
                .filter_by(year=yr)
                .order_by(TradeDetail.week_start)
                .all())
        for t in rows:
            trades_by_owner[t.owner_id].append(t.week_start)

    weeks_json = json.dumps({str(k): v for k, v in trades_by_owner.items()})

    if request.method == "POST":
        return _process_form(owners)

    return render_template("form.html", owners=owners, weeks_json=weeks_json)


def _process_form(owners):
    trade_type = request.form.get("trade_type", "").strip()
    owner1_id = request.form.get("owner1_id", type=int)
    week1 = request.form.get("week1", "").strip()
    owner2_id = request.form.get("owner2_id", type=int)
    week2 = request.form.get("week2", "").strip()
    comment = request.form.get("comment", "").strip()[:40]

    errors = []
    if not trade_type:
        errors.append("Trade type is required.")
    if not owner1_id:
        errors.append("Owner 1 is required.")
    if not week1:
        errors.append("Owner 1 week is required.")
    if trade_type == "Trade Week":
        if not owner2_id:
            errors.append("Owner 2 is required for Trade Week.")
        if not week2:
            errors.append("Owner 2 week is required for Trade Week.")
        if owner1_id and owner2_id and owner1_id == owner2_id:
            errors.append("Owner 1 and Owner 2 must be different.")

    if errors:
        for e in errors:
            flash(e, "error")
        return redirect(url_for("form.form"))

    trade1 = TradeDetail.query.filter_by(
        owner_id=owner1_id, week_start=week1
    ).first()
    if not trade1:
        flash("Week not found for Owner 1.", "error")
        return redirect(url_for("form.form"))

    owner1 = Owner.query.get(owner1_id)

    if trade_type == "Trade Week":
        trade2 = TradeDetail.query.filter_by(
            owner_id=owner2_id, week_start=week2
        ).first()
        if not trade2:
            flash("Week not found for Owner 2.", "error")
            return redirect(url_for("form.form"))

        owner2 = Owner.query.get(owner2_id)

        who_has1 = trade1.calculated_owner or owner1.short_name
        who_has2 = trade2.calculated_owner or owner2.short_name

        trade_comment = (
            f"Traded {owner1.short_name} {week1} For {owner2.short_name} {week2}"
            + (f" {comment}" if comment else "")
        )
        audit_trail = trade_comment

        _update_trade(trade1, owner2, trade_comment, audit_trail)
        _update_trade(trade2, owner1, trade_comment, audit_trail)

        audit = Audit(
            email=session.get("owner_short_name", "unknown"),
            trade_type=trade_type,
            owner1=owner1.short_name,
            owner1_week=week1,
            owner2=owner2.short_name,
            owner2_week=week2,
            comment=comment,
            result1=f"{who_has1}->{owner2.short_name}",
            result2=f"{who_has2}->{owner1.short_name}",
        )
        db.session.add(audit)
        db.session.commit()
        flash(
            f"Trade recorded: {owner1.short_name} {week1} \u2194 {owner2.short_name} {week2}",
            "info",
        )

    else:
        if not comment:
            comment = trade_type
        trade1.comment = comment

        audit = Audit(
            email=session.get("owner_short_name", "unknown"),
            trade_type=trade_type,
            owner1=owner1.short_name,
            owner1_week=week1,
            comment=comment,
        )
        db.session.add(audit)
        db.session.commit()
        flash(f"{trade_type} recorded for {owner1.short_name} week of {week1}", "info")

    return redirect(url_for("calendar.current"))


def _update_trade(trade, new_holder, comment, audit_trail):
    orig_name = trade.owner.short_name
    if not trade.trade_history:
        trade.trade_history = f"{orig_name}->{new_holder.short_name}"
    else:
        trade.trade_history = f"{trade.trade_history}->{new_holder.short_name}"

    trade.is_traded = True
    trade.current_holder_id = new_holder.id
    trade.calculated_owner = new_holder.short_name
    trade.trade_date = datetime.utcnow()
    trade.comment = comment

    if trade.audit_trail:
        trade.audit_trail = f"{trade.audit_trail} | {audit_trail}"
    else:
        trade.audit_trail = audit_trail
