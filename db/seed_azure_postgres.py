#!/usr/bin/env python3
"""
Seed script for Azure PostgreSQL — Ex Libris schema.
Creates library management tables and seeds with property/resident demo data.

Usage:
    export POSTGRES_HOST=aiagent2-pg-dev.postgres.database.azure.com
    export POSTGRES_USER=pgadmin
    export POSTGRES_PASSWORD=<your-password>
    python db/seed_azure_postgres.py
"""

from __future__ import annotations
from datetime import date, datetime, timedelta
from typing import Any
import os

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor, execute_batch, execute_values
except ImportError:
    print("Error: psycopg2 not installed. Run: pip install psycopg2-binary")
    exit(1)

# ─── Connection ────────────────────────────────────────────────

HOST = os.getenv("POSTGRES_HOST", "localhost")
PORT = int(os.getenv("POSTGRES_PORT", "5432"))
DB = os.getenv("POSTGRES_DB", "evieai")
USER = os.getenv("POSTGRES_USER", "postgres")
PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
SSL_MODE = os.getenv("POSTGRES_SSL_MODE", "require")

print(f"Connecting to {HOST}:{PORT}/{DB} as {USER}...")
try:
    conn = psycopg2.connect(
        host=HOST, port=PORT, database=DB, user=USER,
        password=PASSWORD, sslmode=SSL_MODE, connect_timeout=10,
    )
    print("✓ Connected")
except psycopg2.Error as e:
    print(f"✗ Connection failed: {e}")
    exit(1)

conn.autocommit = False
cursor = conn.cursor(cursor_factory=RealDictCursor)

# ─── Create Core Ex Libris Tables ──────────────────────────────

print("\nCreating schema...")

# Library locations
cursor.execute("""
    CREATE TABLE IF NOT EXISTS library (
        library_id SERIAL PRIMARY KEY,
        library_name VARCHAR(50),
        library_display_name VARCHAR(80),
        nuc_code VARCHAR(15)
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS location (
        location_id SERIAL PRIMARY KEY,
        location_code VARCHAR(10),
        location_name VARCHAR(25),
        location_display_name VARCHAR(60),
        library_id INTEGER REFERENCES library(library_id),
        suppress_in_opac CHAR(1) DEFAULT 'N'
    )
""")

# Bibliographic records (Properties)
cursor.execute("""
    CREATE TABLE IF NOT EXISTS bib_master (
        bib_id SERIAL PRIMARY KEY,
        library_id INTEGER REFERENCES library(library_id),
        suppress_in_opac CHAR(1) DEFAULT 'N',
        create_date DATE DEFAULT CURRENT_DATE,
        update_date DATE DEFAULT CURRENT_DATE
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS bib_text (
        bib_id INTEGER PRIMARY KEY REFERENCES bib_master(bib_id),
        title VARCHAR(255),
        author VARCHAR(255),
        publisher VARCHAR(150),
        publication_date VARCHAR(10)
    )
""")

# Holdings (Units)
cursor.execute("""
    CREATE TABLE IF NOT EXISTS mfhd_master (
        mfhd_id SERIAL PRIMARY KEY,
        location_id INTEGER REFERENCES location(location_id),
        call_no_type CHAR(1),
        display_call_no VARCHAR(300),
        suppress_in_opac CHAR(1) DEFAULT 'N',
        create_date DATE DEFAULT CURRENT_DATE,
        update_date DATE DEFAULT CURRENT_DATE
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS bib_mfhd (
        bib_id INTEGER REFERENCES bib_master(bib_id),
        mfhd_id INTEGER REFERENCES mfhd_master(mfhd_id),
        PRIMARY KEY (bib_id, mfhd_id)
    )
""")

# Items (Unit copies)
cursor.execute("""
    CREATE TABLE IF NOT EXISTS item_type (
        item_type_id SERIAL PRIMARY KEY,
        item_type_code VARCHAR(10),
        item_type_name VARCHAR(25),
        item_type_display VARCHAR(40)
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS item (
        item_id SERIAL PRIMARY KEY,
        perm_location INTEGER REFERENCES location(location_id),
        item_type_id INTEGER REFERENCES item_type(item_type_id),
        copy_number INTEGER,
        pieces INTEGER,
        price NUMERIC(12,2),
        create_date DATE DEFAULT CURRENT_DATE,
        modify_date DATE DEFAULT CURRENT_DATE
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS item_barcode (
        item_id INTEGER PRIMARY KEY REFERENCES item(item_id),
        item_barcode VARCHAR(30),
        barcode_status INTEGER
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS mfhd_item (
        mfhd_id INTEGER REFERENCES mfhd_master(mfhd_id),
        item_id INTEGER REFERENCES item(item_id),
        item_enum VARCHAR(80),
        chron VARCHAR(80),
        PRIMARY KEY (mfhd_id, item_id)
    )
""")

# Patron records (Residents)
cursor.execute("""
    CREATE TABLE IF NOT EXISTS patron_group (
        patron_group_id SERIAL PRIMARY KEY,
        patron_group_code VARCHAR(10),
        patron_group_name VARCHAR(25),
        patron_group_display VARCHAR(40)
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS patron (
        patron_id SERIAL PRIMARY KEY,
        patron_group_id INTEGER REFERENCES patron_group(patron_group_id),
        last_name VARCHAR(50),
        first_name VARCHAR(50),
        middle_name VARCHAR(50),
        institution_id VARCHAR(30),
        registration_date DATE DEFAULT CURRENT_DATE,
        create_date DATE DEFAULT CURRENT_DATE,
        modify_date DATE DEFAULT CURRENT_DATE,
        expire_date DATE
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS patron_barcode (
        patron_barcode_id SERIAL PRIMARY KEY,
        patron_id INTEGER REFERENCES patron(patron_id),
        patron_barcode VARCHAR(25),
        barcode_status INTEGER
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS patron_address (
        address_id SERIAL PRIMARY KEY,
        patron_id INTEGER REFERENCES patron(patron_id),
        address_type INTEGER,
        address_line1 VARCHAR(100),
        city VARCHAR(40),
        state_province VARCHAR(7),
        zip_postal VARCHAR(10),
        country VARCHAR(20)
    )
""")

# Circulation (Leases)
cursor.execute("""
    CREATE TABLE IF NOT EXISTS circ_policy_matrix (
        circ_policy_matrix_id SERIAL PRIMARY KEY,
        patron_group_id INTEGER REFERENCES patron_group(patron_group_id),
        item_type_id INTEGER REFERENCES item_type(item_type_id),
        loan_period INTEGER,
        renewal_count INTEGER
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS circ_transactions (
        circ_transaction_id SERIAL PRIMARY KEY,
        item_id INTEGER REFERENCES item(item_id),
        patron_id INTEGER REFERENCES patron(patron_id),
        charge_date DATE DEFAULT CURRENT_DATE,
        due_date DATE,
        discharge_date DATE,
        renewal_count INTEGER DEFAULT 0
    )
""")

conn.commit()
print("✓ Schema ready")

# ─── Seeding ───────────────────────────────────────────────────

print("\nSeeding demo data...")

# Insert library
cursor.execute("""
    INSERT INTO library (library_name, library_display_name, nuc_code)
    VALUES (%s, %s, %s)
    RETURNING library_id
""", ("EvieAI Property System", "EvieAI Properties", "EVA"))
lib_row = cursor.fetchone()
library_id = lib_row["library_id"] if lib_row else 1
conn.commit()

# Insert locations (as properties)
PROPERTIES = [
    {"name": "The Vue at Madison", "code": "TVUE", "units": 240},
    {"name": "Riverside Heights", "code": "RHED", "units": 180},
    {"name": "Oakwood Crossings", "code": "OAKS", "units": 96},
    {"name": "Highland Ridge", "code": "HRID", "units": 64},
    {"name": "The Emerson", "code": "EMER", "units": 312},
    {"name": "Southgate Village", "code": "SGAT", "units": 128},
    {"name": "Poplar Pointe", "code": "PPOI", "units": 72},
    {"name": "Village at Germantown", "code": "VGER", "units": 156},
    {"name": "University Village", "code": "UNIV", "units": 120},
    {"name": "The Gardens at Shelby", "code": "GARD", "units": 90},
    {"name": "Court Square Flats", "code": "CSQU", "units": 24},
    {"name": "Cordova Station", "code": "CORD", "units": 168},
]

location_ids = {}
for prop in PROPERTIES:
    cursor.execute("""
        INSERT INTO location (location_code, location_name, location_display_name, library_id)
        VALUES (%s, %s, %s, %s) RETURNING location_id
    """, (prop["code"], prop["code"], prop["name"], library_id))
    loc_id = cursor.fetchone()["location_id"]
    location_ids[prop["name"]] = loc_id
    print(f"  ✓ Location: {prop['name']}")

conn.commit()

# Insert item types
cursor.execute("""
    INSERT INTO item_type (item_type_code, item_type_name, item_type_display)
    VALUES ('UNIT', 'Unit', 'Residential Unit') RETURNING item_type_id
""")
unit_type_id = cursor.fetchone()["item_type_id"]
conn.commit()

# Insert patron groups
cursor.execute("""
    INSERT INTO patron_group (patron_group_code, patron_group_name, patron_group_display)
    VALUES ('RES', 'Resident', 'Residential Tenant') RETURNING patron_group_id
""")
res_group_id = cursor.fetchone()["patron_group_id"]
conn.commit()

# Insert patrons (Residents)
first_names = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda"]
last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"]

# Insert patrons (Residents) using batch insert
patron_ids = []
patron_rows = []
for i in range(420):
    fname = first_names[i % len(first_names)]
    lname = last_names[i % len(last_names)]
    patron_rows.append((res_group_id, lname, fname, f"RES{i:06d}"))

# Batch insert patrons
execute_batch(cursor, """
    INSERT INTO patron (patron_group_id, last_name, first_name, institution_id)
    VALUES (%s, %s, %s, %s)
""", patron_rows, page_size=100)

# Fetch patron IDs
cursor.execute("SELECT patron_id FROM patron ORDER BY institution_id")
patron_ids = [row["patron_id"] for row in cursor.fetchall()]

print(f"  ✓ {len(patron_ids)} residents")
conn.commit()

# Insert items (Unit copies) using batch insert
item_rows = []
item_barcode_rows = []
for prop in PROPERTIES:
    loc_id = location_ids[prop["name"]]
    for unit_num in range(1, min(prop["units"] + 1, 51)):  # Limit to 50 per property
        item_rows.append((loc_id, unit_type_id, unit_num))
        barcode = f"{loc_id:04d}-{unit_num:04d}"
        item_barcode_rows.append((barcode, 1))

# Batch insert items
execute_batch(cursor, """
    INSERT INTO item (perm_location, item_type_id, copy_number)
    VALUES (%s, %s, %s)
""", item_rows, page_size=100)

# Fetch item IDs
cursor.execute("SELECT item_id FROM item ORDER BY item_id")
item_ids = [row["item_id"] for row in cursor.fetchall()]

# Associate barcodes with items
for idx, item_id in enumerate(item_ids[:len(item_barcode_rows)]):
    item_barcode_rows[idx] = (item_id, item_barcode_rows[idx][0], item_barcode_rows[idx][1])

execute_batch(cursor, """
    INSERT INTO item_barcode (item_id, item_barcode, barcode_status)
    VALUES (%s, %s, %s)
""", item_barcode_rows, page_size=100)

print(f"  ✓ {len(item_ids)} items/units")
conn.commit()

# Insert bib records (Properties) using batch insert
bib_rows = []
bib_text_rows = []
for prop in PROPERTIES:
    bib_rows.append((library_id,))
    bib_text_rows.append((prop["name"], "Property Management", "EvieAI"))

# Insert bibs
execute_batch(cursor, """
    INSERT INTO bib_master (library_id)
    VALUES (%s)
""", bib_rows, page_size=100)

# Fetch bib IDs
cursor.execute("SELECT bib_id FROM bib_master ORDER BY bib_id DESC LIMIT %s", (len(bib_rows),))
bib_ids = [row["bib_id"] for row in reversed(cursor.fetchall())]

# Insert bib text
for idx, bib_id in enumerate(bib_ids):
    bib_text_rows[idx] = (bib_id,) + bib_text_rows[idx]

execute_batch(cursor, """
    INSERT INTO bib_text (bib_id, title, author, publisher)
    VALUES (%s, %s, %s, %s)
""", bib_text_rows, page_size=100)

print(f"  ✓ {len(bib_ids)} property records")
conn.commit()

# Insert holdings (Units per property) using batch insert
mfhd_rows = []
bib_mfhd_rows = []
for idx, prop in enumerate(PROPERTIES):
    loc_id = location_ids[prop["name"]]
    mfhd_rows.append((loc_id, prop["code"]))
    bib_mfhd_rows.append((bib_ids[idx],))

# Insert mfhd records
execute_batch(cursor, """
    INSERT INTO mfhd_master (location_id, display_call_no)
    VALUES (%s, %s)
""", mfhd_rows, page_size=100)

# Fetch mfhd IDs
cursor.execute("SELECT mfhd_id FROM mfhd_master ORDER BY mfhd_id DESC LIMIT %s", (len(mfhd_rows),))
mfhd_ids = [row["mfhd_id"] for row in reversed(cursor.fetchall())]

# Insert bib_mfhd relationships
for idx, mfhd_id in enumerate(mfhd_ids):
    bib_mfhd_rows[idx] = bib_mfhd_rows[idx] + (mfhd_id,)

execute_batch(cursor, """
    INSERT INTO bib_mfhd (bib_id, mfhd_id)
    VALUES (%s, %s)
""", bib_mfhd_rows, page_size=100)

conn.commit()

# Insert circulations (Leases) using batch insert
circ_rows = []
for i in range(min(350, len(patron_ids))):  # Up to 350 leases
    if i < len(item_ids):
        circ_rows.append((item_ids[i], patron_ids[i], date.today() + timedelta(days=365)))

if circ_rows:
    execute_batch(cursor, """
        INSERT INTO circ_transactions (item_id, patron_id, due_date)
        VALUES (%s, %s, %s)
    """, circ_rows, page_size=100)

print(f"  ✓ {len(circ_rows)} leases/circulations")
conn.commit()

print("\n✅ Seed complete!")
cursor.execute("""
    SELECT 
        'libraries' as name, COUNT(*) as count FROM library
    UNION ALL
    SELECT 'locations', COUNT(*) FROM location
    UNION ALL
    SELECT 'patrons', COUNT(*) FROM patron
    UNION ALL
    SELECT 'items', COUNT(*) FROM item
    UNION ALL
    SELECT 'bibs', COUNT(*) FROM bib_master
    UNION ALL
    SELECT 'circulations', COUNT(*) FROM circ_transactions
    ORDER BY name
""")

print("\nDatabase contents:")
for row in cursor.fetchall():
    print(f"  {row['name']:20} {row['count']:6} records")

cursor.close()
conn.close()
print("\n✅ Done!")
