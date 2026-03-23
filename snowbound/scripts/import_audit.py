"""
Import Audit sheet from SnowBoundersCalendarApp.xlsx into audit table.
Reads directly from xlsx — no CSV export required.
Run from project root: python -m snowbound.scripts.import_audit
"""
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import openpyxl
from snowbound import create_app, db
from snowbound.models import Audit

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
XLSX_PATH = os.path.join(PROJECT_ROOT, "SnowBoundersCalendarApp.xlsx")

# Sheet columns (0-indexed):
# 0=Timestamp, 1=yourEmailAddress, 2=tradeType, 3=owner1, 4=owner1Week,
# 5=owner2, 6=owner2Week, 7=comment, 8=AuditRec1, 9=Auditrec2


def _to_date_str(val):
    """Convert xlsx datetime or string to MM/DD/YYYY string, or None."""
    if val is None:
        return None
    if hasattr(val, 'strftime'):
        return val.strftime("%m/%d/%Y")
    s = str(val).strip()
    return s if s else None


def run():
    app = create_app()
    with app.app_context():
        if Audit.query.count() > 0:
            print("audit table already has data — skipping. Delete rows first to re-import.")
            return

        wb = openpyxl.load_workbook(XLSX_PATH, read_only=True, data_only=True)
        ws = wb["Audit"]

        batch = []
        rows_inserted = 0

        for row in ws.iter_rows(min_row=2, values_only=True):
            if not any(v is not None for v in row):
                continue

            # rows may have 8-10 columns depending on how many fields were filled
            row = list(row) + [None] * 10  # pad to at least 10
            timestamp = row[0]
            email = row[1]
            trade_type = row[2]
            owner1 = row[3]
            owner1_week = row[4]
            owner2 = row[5]
            owner2_week = row[6]
            comment = row[7]
            result1 = row[8]
            result2 = row[9]

            if timestamp is None:
                continue

            # timestamp comes as datetime from xlsx
            ts = timestamp if hasattr(timestamp, 'year') else None

            batch.append(Audit(
                timestamp=ts,
                email=str(email).strip().lower() if email else None,
                trade_type=str(trade_type).strip() if trade_type else None,
                owner1=str(owner1).strip() if owner1 else None,
                owner1_week=_to_date_str(owner1_week),
                owner2=str(owner2).strip() if owner2 else None,
                owner2_week=_to_date_str(owner2_week),
                comment=str(comment).strip() if comment else None,
                result1=str(result1).strip() if result1 else None,
                result2=str(result2).strip() if result2 else None,
            ))
            rows_inserted += 1

        db.session.bulk_save_objects(batch)
        db.session.commit()
        wb.close()

        print(f"Inserted {rows_inserted} audit rows.")


if __name__ == "__main__":
    run()
