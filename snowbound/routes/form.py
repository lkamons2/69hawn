import json
from datetime import date, datetime
from collections import defaultdict
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, current_app
from .. import db
from ..models import Owner, TradeDetail, Audit
from ..decorators import login_required
from ..email import send_email, send_trade_notification, get_owner_emails

bp = Blueprint("form", __name__)


@bp.route("/form", methods=["GET", "POST"])
@login_required
def form():
    owners = Owner.query.filter_by(is_active=True).order_by(Owner.name).all()

    today_year = date.today().year
    if current_app.config.get("TESTING_MODE"):
        year_start, year_end = today_year - 3, today_year + 4
    else:
        year_start, year_end = today_year - 1, today_year + 4
    trades_by_owner = defaultdict(list)
    for yr in range(year_start, year_end):
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

        who_has1 = trade1.calculated_owner or owner1.name
        who_has2 = trade2.calculated_owner or owner2.name

        trade_comment = (
            f"Traded {owner1.name} {week1} For {owner2.name} {week2}"
            + (f" {comment}" if comment else "")
        )
        audit_trail = trade_comment

        _update_trade(trade1, owner2, trade_comment, audit_trail)
        _update_trade(trade2, owner1, trade_comment, audit_trail)

        audit = Audit(
            email=f"{session.get('owner_name', 'unknown')} ({session.get('owner_email', '')})",
            trade_type=trade_type,
            owner1=owner1.name,
            owner1_week=week1,
            owner2=owner2.name,
            owner2_week=week2,
            comment=comment,
            result1=f"{who_has1}->{owner2.name}",
            result2=f"{who_has2}->{owner1.name}",
        )
        db.session.add(audit)
        db.session.commit()

        # --- Trade notification email ---
        changed_by = session.get("owner_name", "unknown")
        owner_email_map = [
            (owner1.name, get_owner_emails(owner1)),
            (owner2.name, get_owner_emails(owner2)),
        ]

        # Double-trade: if someone else already held either week, notify them too
        notified = {owner1.name, owner2.name}
        for holder_name in (who_has1, who_has2):
            if holder_name and holder_name not in notified:
                dt_owner = Owner.query.filter_by(name=holder_name).first()
                if dt_owner:
                    owner_email_map.append((dt_owner.name, get_owner_emails(dt_owner)))
                    notified.add(holder_name)

        subject = (
            f"69hawn.com Trade ({owner1.name}) {week1}"
            f" and ({owner2.name}) {week2}"
        )
        body_text = (
            f"Trade: ({owner1.name}) {week1} and ({owner2.name}) {week2}\n\n"
            f"Change made by {changed_by}\n"
        )
        if comment:
            body_text += f"Comment: {comment}\n"
        body_html = f"<html><body>{body_text.replace(chr(10), '<br>')}</body></html>"

        if send_trade_notification(owner_email_map, subject, body_text, body_html):
            flash(
                f"Trade recorded: {owner1.name} {week1} \u2194 {owner2.name} {week2}"
                f" \u2014 email sent",
                "info",
            )
        else:
            flash(
                f"Trade recorded: {owner1.name} {week1} \u2194 {owner2.name} {week2}",
                "info",
            )

    else:
        if not comment:
            comment = trade_type
        trade1.comment = comment

        audit = Audit(
            email=f"{session.get('owner_name', 'unknown')} ({session.get('owner_email', '')})",
            trade_type=trade_type,
            owner1=owner1.name,
            owner1_week=week1,
            comment=comment,
        )
        db.session.add(audit)
        db.session.commit()

        # --- Non-trade notification email ---
        changed_by = session.get("owner_name", "unknown")
        owner_email_map = [(owner1.name, get_owner_emails(owner1))]
        subject = (
            f"69hawn.com Change made to ({owner1.name}) for {week1}"
            f" by {changed_by}"
        )
        body_text = (
            f"Change: {trade_type} for ({owner1.name}) week of {week1}\n\n"
            f"Change made by {changed_by}\n"
            f"Comment: {comment}\n"
        )
        body_html = f"<html><body>{body_text.replace(chr(10), '<br>')}</body></html>"

        if send_trade_notification(owner_email_map, subject, body_text, body_html):
            flash(f"{trade_type} recorded for {owner1.name} week of {week1} \u2014 email sent", "info")
        else:
            flash(f"{trade_type} recorded for {owner1.name} week of {week1}", "info")

    return redirect(url_for("calendar.current"))


def _update_trade(trade, new_holder, comment, audit_trail):
    orig_name = trade.owner.name
    if not trade.trade_history:
        trade.trade_history = f"{orig_name}->{new_holder.name}"
    else:
        trade.trade_history = f"{trade.trade_history}->{new_holder.name}"

    trade.is_traded = True
    trade.current_holder_id = new_holder.id
    trade.calculated_owner = new_holder.name
    trade.trade_date = datetime.utcnow()
    trade.comment = comment

    if trade.audit_trail:
        trade.audit_trail = f"{trade.audit_trail} | {audit_trail}"
    else:
        trade.audit_trail = audit_trail
