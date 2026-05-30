#!/usr/bin/env python3
from __future__ import annotations

import os
import random
from datetime import date, timedelta

import psycopg2


def env(name: str, default: str) -> str:
    return os.getenv(name, default)


def main() -> None:
    host = env("POSTGRES_HOST", "aiagent2-pg-dev.postgres.database.azure.com")
    port = int(env("POSTGRES_PORT", "5432"))
    db = env("POSTGRES_DB", "aiagent2_postgres_dev")
    user = env("POSTGRES_USER", "pgadmin")
    password = env("POSTGRES_PASSWORD", "")

    if not password:
        raise SystemExit("POSTGRES_PASSWORD is required")

    conn = psycopg2.connect(
        host=host,
        port=port,
        dbname=db,
        user=user,
        password=password,
        sslmode="require",
    )
    conn.autocommit = False

    with conn, conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS properties (
              id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              city TEXT,
              state TEXT
            );

            CREATE TABLE IF NOT EXISTS units (
              id TEXT PRIMARY KEY,
              property_id TEXT REFERENCES properties(id),
              unit_number TEXT NOT NULL,
              bedrooms INTEGER,
              bathrooms NUMERIC(3,1)
            );

            CREATE TABLE IF NOT EXISTS residents (
              id TEXT PRIMARY KEY,
              full_name TEXT NOT NULL,
              email TEXT,
              phone TEXT
            );

            CREATE TABLE IF NOT EXISTS leases (
              id TEXT PRIMARY KEY,
              resident_id TEXT REFERENCES residents(id),
              unit_id TEXT REFERENCES units(id),
              start_date DATE,
              end_date DATE,
              monthly_rent NUMERIC(10,2)
            );

            CREATE TABLE IF NOT EXISTS work_orders (
              id TEXT PRIMARY KEY,
              property_id TEXT REFERENCES properties(id),
              unit_id TEXT REFERENCES units(id),
              type TEXT NOT NULL,
              status TEXT NOT NULL,
              priority TEXT,
              created_at DATE NOT NULL,
              completed_at DATE
            );

            CREATE TABLE IF NOT EXISTS charges (
              id TEXT PRIMARY KEY,
              lease_id TEXT REFERENCES leases(id),
              charge_type TEXT NOT NULL,
              amount NUMERIC(10,2) NOT NULL,
              posted_on DATE NOT NULL
            );
            """
        )

        cur.execute("SELECT COUNT(*) FROM work_orders")
        work_order_count = cur.fetchone()[0]
        if work_order_count >= 50:
            print(f"Seed already present (work_orders={work_order_count}).")
            return

        properties = [
            ("prop-001", "The Vue at Madison", "Memphis", "TN"),
            ("prop-002", "Riverside Heights", "Memphis", "TN"),
            ("prop-003", "Village at Germantown", "Germantown", "TN"),
        ]
        for row in properties:
            cur.execute(
                """
                INSERT INTO properties (id, name, city, state)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                row,
            )

        units = []
        for p in properties:
            for i in range(1, 21):
                units.append((f"unit-{p[0]}-{i:03d}", p[0], f"{100+i}", random.choice([1, 2, 3]), random.choice([1.0, 1.5, 2.0])))

        for row in units:
            cur.execute(
                """
                INSERT INTO units (id, property_id, unit_number, bedrooms, bathrooms)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                row,
            )

        residents = []
        for i in range(1, 61):
            residents.append((f"res-{i:03d}", f"Resident {i}", f"resident{i}@example.com", f"901-555-{1000+i:04d}"))

        for row in residents:
            cur.execute(
                """
                INSERT INTO residents (id, full_name, email, phone)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                row,
            )

        leases = []
        today = date.today()
        for i in range(1, 61):
            start = today - timedelta(days=random.randint(30, 540))
            end = start + timedelta(days=365)
            leases.append((
                f"lease-{i:03d}",
                f"res-{i:03d}",
                units[(i - 1) % len(units)][0],
                start,
                end,
                random.choice([1200, 1350, 1500, 1650, 1850]),
            ))

        for row in leases:
            cur.execute(
                """
                INSERT INTO leases (id, resident_id, unit_id, start_date, end_date, monthly_rent)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                row,
            )

        wo_types = ["Plumbing", "HVAC", "Electrical", "Appliance", "Paint", "Pest Control"]
        statuses = ["Open", "In Progress", "Completed"]
        priorities = ["Low", "Medium", "High", "Urgent"]

        work_orders = []
        for i in range(1, 121):
            created = today - timedelta(days=random.randint(0, 120))
            status = random.choice(statuses)
            completed = created + timedelta(days=random.randint(1, 10)) if status == "Completed" else None
            work_orders.append((
                f"wo-{i:04d}",
                random.choice(properties)[0],
                random.choice(units)[0],
                random.choice(wo_types),
                status,
                random.choice(priorities),
                created,
                completed,
            ))

        for row in work_orders:
            cur.execute(
                """
                INSERT INTO work_orders (id, property_id, unit_id, type, status, priority, created_at, completed_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                row,
            )

        charges = []
        for i in range(1, 121):
            charges.append((
                f"chg-{i:04d}",
                f"lease-{((i - 1) % 60) + 1:03d}",
                random.choice(["Rent", "Pet Fee", "Late Fee", "Utility"]),
                random.choice([50, 75, 100, 125, 150, 1200, 1350]),
                today - timedelta(days=random.randint(0, 90)),
            ))

        for row in charges:
            cur.execute(
                """
                INSERT INTO charges (id, lease_id, charge_type, amount, posted_on)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                row,
            )

        cur.execute("SELECT COUNT(*) FROM work_orders")
        wc = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM properties")
        pc = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM units")
        uc = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM residents")
        rc = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM leases")
        lc = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM charges")
        cc = cur.fetchone()[0]

        print(f"Seed complete. properties={pc}, units={uc}, residents={rc}, leases={lc}, work_orders={wc}, charges={cc}")


if __name__ == "__main__":
    main()
