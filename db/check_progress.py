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

queries = [
    ('Location (Properties)', 'SELECT COUNT(*) FROM location'),
    ('Patron (Residents)', 'SELECT COUNT(*) FROM patron'),
    ('Item (Units)', 'SELECT COUNT(*) FROM item'),
    ('Circ_transactions (Leases)', 'SELECT COUNT(*) FROM circ_transactions'),
    ('Bib_master (Property Records)', 'SELECT COUNT(*) FROM bib_master'),
]

for label, query in queries:
    cursor.execute(query)
    count = cursor.fetchone()[0]
    print(f'{label}: {count}')

conn.close()
