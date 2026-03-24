"""
Generate calendar + mud_weeks tables from 2022 to 2100.
Safe to re-run: clears existing rows first.
Run from project root: python -m snowbound.scripts.generate_rotation
"""
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from snowbound import create_app, db
from snowbound.models import Owner, Calendar, MudWeek

# Rotation order — Loyle appears twice (positions 1 and 10)
OWNER_NAMES = [
    "Loyle", "Zerfas", "Sproul", "Miller", "Stalker",
    "Smith", "Boone", "Kamons", "Mitchell", "Loyle",
]

START_YEAR = 2022
END_YEAR = 2100


def count_thursdays(year):
    first_day = datetime(year, 1, 1)
    last_day = datetime(year, 12, 31)
    first_thursday = first_day + timedelta((3 - first_day.weekday() + 7) % 7)
    return (last_day - first_thursday).days // 7 + 1


def get_mud_weeks(year):
    first_may = datetime(year, 5, 1)
    first_thursday_in_may = first_may + timedelta((3 - first_may.weekday() + 7) % 7)
    num_thursdays = count_thursdays(year)
    num_mud_weeks = 4 if num_thursdays == 53 else 3
    return [first_thursday_in_may + timedelta(weeks=i) for i in range(num_mud_weeks)]


def run():
    app = create_app()
    with app.app_context():
        # Build owner lookup: name -> id
        owner_map = {o.name: o.id for o in Owner.query.all()}
        missing = set(OWNER_NAMES) - set(owner_map.keys())
        if missing:
            print(f"ERROR: owners not found in DB: {missing}")
            print("Run seed_owners.py first.")
            sys.exit(1)

        # Clear existing rows
        db.session.execute(db.text("DELETE FROM calendar"))
        db.session.execute(db.text("DELETE FROM mud_weeks"))
        db.session.commit()
        print("Cleared calendar and mud_weeks tables.")

        calendar_rows = []
        mud_rows = []
        last_owner_index = 0

        for year in range(START_YEAR, END_YEAR + 1):
            mud_weeks = get_mud_weeks(year)
            mud_week_dates = set(mw.date() for mw in mud_weeks)

            # Mud weeks rows — one per mud week date
            num_thursdays = count_thursdays(year)
            num_mud_weeks = len(mud_weeks)
            for mw in mud_weeks:
                mud_rows.append(MudWeek(
                    year=year,
                    week_start=mw.strftime("%m/%d/%Y"),
                    num_mud_weeks=num_mud_weeks,
                    num_thursdays=num_thursdays,
                ))

            # Rotation for this year
            rotated_owners = OWNER_NAMES[last_owner_index:] + OWNER_NAMES[:last_owner_index]
            owner_index = 0
            # Track weeks per slot in rotated order
            owner_week_lists = [[] for _ in rotated_owners]

            current_date = datetime(year, 1, 1) + timedelta((3 - datetime(year, 1, 1).weekday() + 7) % 7)
            while current_date.year == year:
                if current_date.date() not in mud_week_dates:
                    owner_week_lists[owner_index].append(current_date.strftime("%m/%d/%Y"))
                    owner_index = (owner_index + 1) % len(rotated_owners)
                current_date += timedelta(weeks=1)

            # Insert calendar rows — track week_number per owner across all slots
            owner_week_counts = {}
            for slot_idx, (name, weeks) in enumerate(zip(rotated_owners, owner_week_lists)):
                oid = owner_map[name]
                start = owner_week_counts.get(oid, 0)
                for i, week_start in enumerate(weeks):
                    calendar_rows.append(Calendar(
                        year=year,
                        owner_id=oid,
                        week_start=week_start,
                        week_number=start + i + 1,
                    ))
                owner_week_counts[oid] = start + len(weeks)

            last_owner_index = (last_owner_index + owner_index) % len(OWNER_NAMES)

        db.session.bulk_save_objects(calendar_rows)
        db.session.bulk_save_objects(mud_rows)
        db.session.commit()

        cal_count = db.session.execute(db.text("SELECT COUNT(*) FROM calendar")).scalar()
        mud_count = db.session.execute(db.text("SELECT COUNT(*) FROM mud_weeks")).scalar()
        print(f"Inserted {cal_count} calendar rows.")
        print(f"Inserted {mud_count} mud_weeks rows.")


if __name__ == "__main__":
    run()
