"""
Import TradeDetail sheet from SnowBoundersCalendarApp.xlsx into trade_detail table.
Reads directly from xlsx — no CSV export required.
Run from project root: python -m snowbound.scripts.import_trade_detail
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import openpyxl
from snowbound import create_app, db
from snowbound.models import Owner, TradeDetail

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
XLSX_PATH = os.path.join(PROJECT_ROOT, "GAS-code", "SnowBoundersCalendarApp.xlsx")

# Sheet columns (0-indexed):
# 0=YEAR, 1=NAME, 2=Week, 3=Traded, 4=Who Has Condo,
# 5=Trade Date, 6=Trade History, 7=Comment, 8=AuditTrail, 9=CalculatedOwner


def run():
    app = create_app()
    with app.app_context():
        if TradeDetail.query.count() > 0:
            print("trade_detail already has data — skipping. Delete rows first to re-import.")
            return

        owner_map = {o.short_name: o.id for o in Owner.query.all()}
        if not owner_map:
            print("ERROR: owners table is empty. Run seed_owners.py first.")
            sys.exit(1)

        wb = openpyxl.load_workbook(XLSX_PATH, read_only=True, data_only=True)
        ws = wb["TradeDetail"]

        rows_inserted = 0
        skipped = 0
        name_mismatches = set()

        batch = []
        for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True)):
            if not any(v is not None for v in row):
                continue

            year_val = row[0]
            name = row[1]
            week_start = row[2]
            traded = row[3]
            who_has = row[4]
            trade_date = row[5]
            trade_history = row[6]
            comment = row[7]
            audit_trail = row[8]
            calc_owner = row[9] if len(row) > 9 else None

            if year_val is None or name is None or week_start is None:
                continue

            year = int(year_val)
            name = str(name).strip()

            if name not in owner_map:
                name_mismatches.add(name)
                skipped += 1
                continue

            owner_id = owner_map[name]

            # current_holder_id: default to owner_id if no trade
            current_holder_id = owner_id
            if who_has and str(who_has).strip():
                holder_name = str(who_has).strip()
                if holder_name in owner_map:
                    current_holder_id = owner_map[holder_name]
                else:
                    name_mismatches.add(f"holder:{holder_name}")

            is_traded = bool(traded and str(traded).strip().upper() in ("Y", "YES", "TRUE", "1"))

            # trade_date comes as datetime from xlsx
            trade_date_val = trade_date if hasattr(trade_date, 'year') else None

            batch.append(TradeDetail(
                year=year,
                owner_id=owner_id,
                week_start=str(week_start).strip(),
                is_traded=is_traded,
                current_holder_id=current_holder_id,
                trade_date=trade_date_val,
                trade_history=str(trade_history).strip() if trade_history else None,
                comment=str(comment).strip() if comment else None,
                audit_trail=str(audit_trail).strip() if audit_trail else None,
                calculated_owner=str(calc_owner).strip() if calc_owner else None,
            ))
            rows_inserted += 1

            if len(batch) >= 500:
                db.session.bulk_save_objects(batch)
                db.session.commit()
                batch = []

        if batch:
            db.session.bulk_save_objects(batch)
            db.session.commit()

        wb.close()

        if name_mismatches:
            print(f"WARNING: unrecognized names (skipped {skipped} rows): {sorted(name_mismatches)}")
        print(f"Inserted {rows_inserted} trade_detail rows.")


if __name__ == "__main__":
    run()
