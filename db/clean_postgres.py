import os

import psycopg2

conn = psycopg2.connect(
    host=os.getenv('POSTGRES_HOST'),
    port=int(os.getenv('POSTGRES_PORT', 5432)),
    database=os.getenv('POSTGRES_DB'),
    user=os.getenv('POSTGRES_USER'),
    password=os.getenv('POSTGRES_PASSWORD'),
    sslmode=os.getenv('POSTGRES_SSL_MODE', 'require'),
)

cursor = conn.cursor()

# Drop all tables in order (respect foreign keys)
tables_to_drop = [
    'bib_mfhd',
    'circ_transactions',
    'item_barcode',
    'patron_barcode',
    'patron_address',
    'item',
    'mfhd_master',
    'bib_text',
    'bib_master',
    'patron',
    'patron_group',
    'item_type',
    'location',
    'library',
]

for table in tables_to_drop:
    try:
        cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
        print(f"✓ Dropped {table}")
    except Exception as e:
        print(f"✗ Error dropping {table}: {e}")

conn.commit()
cursor.close()
conn.close()
print("\n✓ Database cleaned")
