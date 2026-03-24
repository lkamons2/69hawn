"""
Seeds owners + owner_emails tables from NameList data.
Run from project root: python -m snowbound.scripts.seed_owners
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from snowbound import create_app, db
from snowbound.models import Owner, OwnerEmail, SiteConfig

# Data extracted from GAS-code/SnowBoundersCalendarApp.xlsx NameList sheet
# Format: (name, notes, contacts_list)
# contacts_list: list of (contact_name, email, phone, is_primary, is_admin)
OWNERS = [
    (
        "Boone", None,
        [("Jim", "itchyboone@yahoo.com", "316-393-7390", True, False)],
    ),
    (
        "Kamons", None,
        [
            ("Larry", "larry@kamons.com", "412-537-2486", True, True),
            ("Maureen", "maureen@kamons.com", "412-965-2020", False, False),
        ],
    ),
    (
        "Loyle", None,
        [("Pam", "ployle3@gmail.com", "316-253-5999", True, False)],
    ),
    (
        "Miller", None,
        [
            ("Stan", "stanmillerict@gmail.com", "316-461-2143", True, False),
            ("Joni", "vchornets1975@yahoo.com", None, False, False),
            ("Morgan", "morgan.lucille3@gmail.com", None, False, False),
        ],
    ),
    (
        "Mitchell", None,
        [("Linda", "lindakmitchell.lkm@gmail.com", "913-226-5699", True, False)],
    ),
    (
        "Smith", None,
        [
            ("Brad", "briarfox10@gmail.com", "316-308-7803", True, False),
            ("Cathrine", "wichitahomeprovider@yahoo.com", "316-371-1128", False, False),
        ],
    ),
    (
        "Sproul", "Land Line 316-260-1005",
        [
            ("Dave", "sproulcons@gmail.com", "316-644-9444", True, False),
            ("Sid", "sproul2071@gmail.com", None, False, False),
        ],
    ),
    (
        "Stalker", None,
        [
            ("Dave", "daves@dsfinancialgroup.com", "316-655-2536", True, False),
            ("Sharon", None, "316-634-2074", False, False),
        ],
    ),
    (
        "Zerfas", None,
        [
            ("Bob", "zerfas.bob@gmail.com", "678-410-6828", True, False),
            ("Dave", "davezerfas12@gmail.com", "217-553-2845", False, False),
        ],
    ),
]

SITE_CONFIG = [
    ("Garage", "2071", "#67 Patsy and Doug Lange h: 303-791-7521  c: 720-334-2933"),
    ("WiFi", "9706683418", "#71 Priscilla & Carmen Cornelio 520-591-7236"),
    ("Lock Box", "4926", ""),
]


def run():
    app = create_app()
    with app.app_context():
        if Owner.query.count() > 0:
            print("owners table already has data — skipping. Delete rows first to re-seed.")
            return

        for name, notes, contacts in OWNERS:
            owner = Owner(
                name=name,
                notes=notes,
                is_active=True,
            )
            db.session.add(owner)
            db.session.flush()  # get owner.id

            for contact_name, email, phone, is_primary, is_admin in contacts:
                db.session.add(OwnerEmail(
                    owner_id=owner.id,
                    name=contact_name,
                    email=email.lower().strip() if email else "",
                    phone=phone,
                    is_primary=is_primary,
                    is_admin=is_admin,
                ))

        for key, value, note in SITE_CONFIG:
            db.session.add(SiteConfig(key=key, value=value, note=note))

        db.session.commit()

        print(f"Inserted {Owner.query.count()} owners.")
        print(f"Inserted {OwnerEmail.query.count()} owner emails.")
        print(f"Inserted {SiteConfig.query.count()} site_config rows.")


if __name__ == "__main__":
    run()
