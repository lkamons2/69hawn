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
# Format: (short_name, full_name, phone, display_info, is_admin, emails_list)
# emails_list: list of (email, is_primary)
OWNERS = [
    (
        "Boone",
        "Jim & Janice Boone",
        "316-393-7390",
        "Jim & Janice Boone\nitchyboone@yahoo.com\n316-393-7390",
        False,
        [("itchyboone@yahoo.com", True)],
    ),
    (
        "Kamons",
        "Larry & Maureen Kamons",
        "Larry cell 412-537-2486\nMaureen cell 412-965-2020",
        "Larry & Maureen Kamons\nlarry@kamons.com\nmaureen@kamons.com\nLarry cell 412-537-2486\nMaureen cell 412-965-2020",
        True,  # is_admin
        [("larry@kamons.com", True, True), ("maureen@kamons.com", False, False)],
    ),
    (
        "Loyle",
        "Pam Loyle",
        "Cell 316-253-5999",
        "Pam Loyle\nployle3@gmail.com\nCell 316-253-5999",
        False,
        [("ployle3@gmail.com", True)],
    ),
    (
        "Miller",
        "Stan & Joni Miller",
        "316-461-2143",
        "Stan & Joni Miller\nstanmillerict@gmail.com\nvchornets1975@yahoo.com\nMorgan.lucille3@gmail.com\n316-461-2143",
        False,
        [
            ("stanmillerict@gmail.com", True),
            ("vchornets1975@yahoo.com", False),
            ("morgan.lucille3@gmail.com", False),
        ],
    ),
    (
        "Mitchell",
        "Linda Mitchell",
        "913-226-5699",
        "Linda Mitchell\nlindakmitchell.lkm@gmail.com\n913-226-5699",
        False,
        [("lindakmitchell.lkm@gmail.com", True)],
    ),
    (
        "Smith",
        "Brad & Cathrine Smith",
        "316-308-7803\n316-371-1128",
        "Brad & Cathrine Smith\nbriarfox10@gmail.com\nwichitahomeprovider@yahoo.com\n316-308-7803\n316-371-1128",
        False,
        [("briarfox10@gmail.com", True), ("wichitahomeprovider@yahoo.com", False)],
    ),
    (
        "Sproul",
        "Dave & Sid Sproul",
        "Dave Cell 316-644-9444\nLand Line 316-260-1005",
        "Dave & Sid Sproul\nsproulcons@gmail.com\nsproul2071@gmail.com\nDave Cell 316-644-9444\nLand Line 316-260-1005",
        False,
        [("sproulcons@gmail.com", True), ("sproul2071@gmail.com", False)],
    ),
    (
        "Stalker",
        "Dave & Sharon Stalker",
        "316-655-2536\n316-634-2074",
        "Dave & Sharon Stalker\ndaves@dsfinancialgroup.com\n316-655-2536\n316-634-2074",
        False,
        [("daves@dsfinancialgroup.com", True)],
    ),
    (
        "Zerfas",
        "Dave & Bob Zerfas",
        "678-410-6828\n217-553-2845",
        "Dave & Bob Zerfas\nzerfas.bob@gmail.com\ndavezerfas12@gmail.com\n678-410-6828\n217-553-2845",
        False,
        [("zerfas.bob@gmail.com", True), ("davezerfas12@gmail.com", False)],
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

        for short_name, full_name, phone, display_info, is_admin, emails in OWNERS:
            owner = Owner(
                short_name=short_name,
                full_name=full_name,
                phone=phone,
                display_info=display_info,
                is_admin=is_admin,
                is_active=True,
            )
            db.session.add(owner)
            db.session.flush()  # get owner.id

            for email_tuple in emails:
                email, is_primary = email_tuple[0], email_tuple[1]
                is_admin_email = email_tuple[2] if len(email_tuple) > 2 else False
                db.session.add(OwnerEmail(
                    owner_id=owner.id,
                    email=email.lower().strip(),
                    is_primary=is_primary,
                    is_admin=is_admin_email,
                ))

        for key, value, note in SITE_CONFIG:
            db.session.add(SiteConfig(key=key, value=value, note=note))

        db.session.commit()

        print(f"Inserted {Owner.query.count()} owners.")
        print(f"Inserted {OwnerEmail.query.count()} owner emails.")
        print(f"Inserted {SiteConfig.query.count()} site_config rows.")


if __name__ == "__main__":
    run()
