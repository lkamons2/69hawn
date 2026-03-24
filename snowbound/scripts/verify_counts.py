"""
Print row counts for all tables and spot-check key data.
Run from project root: python -m snowbound.scripts.verify_counts
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from snowbound import create_app, db


def run():
    app = create_app()
    with app.app_context():
        tables = [
            ("owners",        "10 owners (9 families — Loyle counted once)"),
            ("owner_emails",  "~14 emails total"),
            ("calendar",      "~3,900 rows (2022-2100)"),
            ("mud_weeks",     "~240-260 rows (3-4/year × 79 years)"),
            ("trade_detail",  "~3,921 rows (matches TradeDetail sheet)"),
            ("audit",         "~105 rows (matches Audit sheet)"),
            ("site_config",   "3 rows (Garage, WiFi, Lock Box)"),
            ("magic_links",   "0 (empty)"),
            ("field_definitions", "0 (populated later)"),
            ("lov_values",    "0 (populated later)"),
        ]

        print(f"\n{'Table':<20} {'Count':>8}  {'Expected'}")
        print("-" * 65)
        all_ok = True
        for table, expected in tables:
            count = db.session.execute(db.text(f"SELECT COUNT(*) FROM {table}")).scalar()
            print(f"{table:<20} {count:>8}  {expected}")

        # Spot checks
        print("\n--- Spot checks ---")

        # 2025 calendar: should have 10 owners × some weeks
        rows_2025 = db.session.execute(db.text(
            "SELECT o.name, COUNT(*) as cnt FROM calendar c "
            "JOIN owners o ON c.owner_id = o.id WHERE c.year = 2025 "
            "GROUP BY o.name ORDER BY o.name"
        )).fetchall()
        print("\n2025 calendar weeks by owner:")
        for name, cnt in rows_2025:
            print(f"  {name}: {cnt}")

        # Mud weeks for 2025
        mud_2025 = db.session.execute(db.text(
            "SELECT week_start, num_mud_weeks, num_thursdays FROM mud_weeks WHERE year = 2025 ORDER BY week_start"
        )).fetchall()
        print(f"\n2025 mud weeks ({len(mud_2025)} weeks):")
        for row in mud_2025:
            print(f"  {row[0]}  (year has {row[2]} Thursdays, {row[1]} mud weeks)")

        # Traded rows
        traded_count = db.session.execute(db.text("SELECT COUNT(*) FROM trade_detail WHERE is_traded = 1")).scalar()
        print(f"\nTrades recorded: {traded_count}")

        # Oldest and newest audit timestamps
        ts_range = db.session.execute(db.text(
            "SELECT MIN(timestamp), MAX(timestamp) FROM audit"
        )).fetchone()
        print(f"\nAudit timestamp range: {ts_range[0]} to {ts_range[1]}")

        print()


if __name__ == "__main__":
    run()
