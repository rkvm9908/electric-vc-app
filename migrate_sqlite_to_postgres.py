"""
Migrate all existing data from your old SQLite database (database.db) into
your new Neon Postgres database.

USAGE:
1. Place your old `database.db` file in the same folder as this script.
2. Make sure your project's app.py / models.py are also in this folder
   (or on the Python path) — this script reuses your existing models.
3. Set the DATABASE_URL environment variable to your Neon connection string.
4. Run:
       pip install -r requirements.txt
       export DATABASE_URL="postgresql://user:password@ep-xxxx.neon.tech/dbname?sslmode=require"
       python migrate_sqlite_to_postgres.py

This will:
- Create all tables in Postgres (if not already created)
- Copy every row from SQLite -> Postgres, table by table, in an order that
  respects foreign keys (stations -> branches -> users -> slots -> bookings
  -> feedbacks)
- Skip rows that already exist (matched by primary key) so it's safe to
  re-run if something fails partway through
- Reset Postgres's auto-increment sequences afterward, so new rows created
  by your app don't collide with the migrated IDs
"""
import os
import sqlite3
import sys

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("ERROR: Set DATABASE_URL to your Neon Postgres connection string first.")
    sys.exit(1)

if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

SQLITE_PATH = os.path.join(os.path.dirname(__file__), 'instance/database.db')
if not os.path.exists(SQLITE_PATH):
    print(f"ERROR: {SQLITE_PATH} not found. Put your old database.db next to this script.")
    sys.exit(1)

# Import your app's models so the Postgres schema matches exactly
os.environ['DATABASE_URL'] = DATABASE_URL
from app import app  # noqa: E402
from models import db, User, Station, Branch, Slot, Booking, Feedback  # noqa: E402

# Order matters: parents before children (foreign keys)
TABLES_IN_ORDER = [
    ('stations', Station, 'stations'),
    ('branches', Branch, 'branches'),
    ('users', User, 'users'),
    ('slots', Slot, 'slots'),
    ('bookings', Booking, 'bookings'),
    ('feedbacks', Feedback, 'feedbacks'),
]


def get_sqlite_rows(table_name):
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(f'SELECT * FROM {table_name}')
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows


def migrate():
    with app.app_context():
        print("Creating tables in Postgres (if they don't already exist)...")
        db.create_all()

        for sqlite_table, model, pg_table in TABLES_IN_ORDER:
            rows = get_sqlite_rows(sqlite_table)
            print(f"\n{sqlite_table}: {len(rows)} rows found in SQLite")

            inserted, skipped = 0, 0
            for row in rows:
                pk = row.get('id')
                existing = model.query.get(pk) if pk is not None else None
                if existing:
                    skipped += 1
                    continue

                # Map DB column names -> the actual Python attribute name
                # used on the model (e.g. the 'branch_name' DB column maps
                # to the '_branch_name' Python attribute on Slot, because
                # 'branch_name' itself is a read-only @property).
                column_to_attr = {
                    col.name: attr_name
                    for attr_name, col in model.__mapper__.columns.items()
                }
                clean_row = {
                    column_to_attr[k]: v
                    for k, v in row.items()
                    if k in column_to_attr
                }

                db.session.add(model(**clean_row))
                inserted += 1

            db.session.commit()
            print(f"  -> inserted {inserted}, skipped {skipped} (already existed)")

        # Reset Postgres auto-increment sequences so future inserts don't
        # collide with the migrated IDs
        print("\nResetting auto-increment sequences...")
        for sqlite_table, model, pg_table in TABLES_IN_ORDER:
            db.session.execute(
                db.text(
                    f"SELECT setval(pg_get_serial_sequence('{pg_table}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM {pg_table}), 1))"
                )
            )
        db.session.commit()

        print("\nMigration complete!")


if __name__ == '__main__':
    migrate()