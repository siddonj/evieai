import psycopg2
from psycopg2.extras import RealDictCursor
import os

conn = psycopg2.connect(
    host=os.getenv('POSTGRES_HOST'),
    port=int(os.getenv('POSTGRES_PORT', 5432)),
    database=os.getenv('POSTGRES_DB'),
    user=os.getenv('POSTGRES_USER'),
    password=os.getenv('POSTGRES_PASSWORD'),
    sslmode=os.getenv('POSTGRES_SSL_MODE', 'require'),
)

cursor = conn.cursor(cursor_factory=RealDictCursor)

# Sample queries to verify data
print("📊 Database Verification\n")

print("🏢 Properties (Locations):")
cursor.execute("SELECT location_id, location_code, location_name FROM location ORDER BY location_name LIMIT 5")
for row in cursor.fetchall():
    print(f"  {row['location_code']:10} {row['location_name']}")

print("\n👥 Residents (Patrons) - Sample:")
cursor.execute("SELECT patron_id, first_name, last_name FROM patron ORDER BY patron_id LIMIT 5")
for row in cursor.fetchall():
    print(f"  {row['first_name']} {row['last_name']}")

print("\n🏠 Units (Items) - Sample:")
cursor.execute("SELECT item_id, item_barcode FROM item_barcode ORDER BY item_id LIMIT 5")
for row in cursor.fetchall():
    print(f"  Barcode: {row['item_barcode']}")

print("\n📋 Leases (Circulations) - Sample:")
cursor.execute("SELECT circ_transactions.circ_transaction_id, patron.first_name, patron.last_name, item_barcode.item_barcode FROM circ_transactions JOIN patron ON circ_transactions.patron_id = patron.patron_id JOIN item_barcode ON circ_transactions.item_id = item_barcode.item_id ORDER BY circ_transactions.circ_transaction_id LIMIT 3")
for row in cursor.fetchall():
    print(f"  {row['first_name']} {row['last_name']} - Unit {row['item_barcode']}")

print("\n✅ Verification complete!")

cursor.close()
conn.close()
