"""One-off seed script — populates multifamily & brokerage demo data.
Safe to re-run — only inserts additional records below target count."""
from __future__ import annotations

from datetime import date, timedelta
import os
import re
import time

import pyodbc

raw = os.environ["DATABASE_CONNECTION_STRING"]

TARGET_PROPERTIES = 12
TARGET_CONTACTS = 20
TARGET_DEALS = 12
TARGET_ACTIVITIES = 24
TARGET_UNITS = 24
TARGET_RESIDENTS = 18
TARGET_LEASES = 18
TARGET_WORK_ORDERS = 20
TARGET_CHARGES = 36
TARGET_R1_SITES = 8
TARGET_R1_DEVICES = 96
TARGET_R1_DEVICE_EVENTS = 12000
TARGET_R1_DAILY_METRICS = 35040


def _extract(pattern: str, s: str) -> str:
    m = re.search(pattern, s, re.IGNORECASE)
    return m.group(1) if m else ""


server = _extract(r"Server=tcp:([^;,]+)", raw) + ",1433"
database = _extract(r"Initial Catalog=([^;]+)", raw)
uid = _extract(r"User ID=([^;]+)", raw)
pwd = _extract(r"Password=([^;]+)", raw)

odbc_conn = (
    f"DRIVER={{ODBC Driver 18 for SQL Server}};"
    f"SERVER={server};DATABASE={database};UID={uid};PWD={pwd};"
    f"Encrypt=yes;TrustServerCertificate=no;Connection Timeout=90;"
)

print(f"Connecting to {server} / {database} ...")
for attempt in range(1, 7):
    try:
        conn = pyodbc.connect(odbc_conn, timeout=90)
        print("Connected.")
        break
    except pyodbc.Error as e:
        print(f"Attempt {attempt}/6 failed: {e}. Retrying in 20s...")
        time.sleep(20)
else:
    raise RuntimeError("Could not connect after 6 attempts.")
cursor = conn.cursor()

# ─── Apply migration: create tables (idempotent) ──────────────────────

cursor.execute("""
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'properties')
CREATE TABLE properties (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(100) NOT NULL,
    address NVARCHAR(200), city NVARCHAR(50), state NVARCHAR(20), zip NVARCHAR(10),
    property_type NVARCHAR(50) DEFAULT 'Multifamily',
    total_units INT, year_built INT, building_size_sqft DECIMAL(12,0), lot_size_acres DECIMAL(8,2),
    units_occupied INT, average_rent DECIMAL(8,2), noi DECIMAL(14,2), cap_rate DECIMAL(5,2), estimated_value DECIMAL(14,2),
    owner NVARCHAR(100), property_manager NVARCHAR(100), status NVARCHAR(50) DEFAULT 'Active',
    amenities NVARCHAR(MAX), notes NVARCHAR(MAX),
    created_at DATETIME DEFAULT GETDATE(), updated_at DATETIME DEFAULT GETDATE()
)
""")
cursor.execute("""
IF EXISTS (SELECT 1 FROM sys.tables WHERE name = 'contacts')
   AND NOT EXISTS (
       SELECT 1 FROM sys.columns
       WHERE object_id = OBJECT_ID('contacts') AND name = 'role'
   )
DROP TABLE contacts
""")
cursor.execute("""
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'contacts')
CREATE TABLE contacts (
    id INT IDENTITY(1,1) PRIMARY KEY,
    first_name NVARCHAR(50) NOT NULL, last_name NVARCHAR(50) NOT NULL,
    email NVARCHAR(100), phone NVARCHAR(30), company NVARCHAR(100), job_title NVARCHAR(100),
    role NVARCHAR(50) DEFAULT 'Owner', property_id INT, notes NVARCHAR(MAX),
    created_at DATETIME DEFAULT GETDATE()
)
""")
cursor.execute("""
IF EXISTS (SELECT 1 FROM sys.tables WHERE name = 'deals')
   AND NOT EXISTS (
       SELECT 1 FROM sys.columns
       WHERE object_id = OBJECT_ID('deals') AND name = 'deal_type'
   )
DROP TABLE deals
""")
cursor.execute("""
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'deals')
CREATE TABLE deals (
    id INT IDENTITY(1,1) PRIMARY KEY,
    property_id INT, deal_type NVARCHAR(50) DEFAULT 'Sale',
    stage NVARCHAR(50) DEFAULT 'LOI', buyer NVARCHAR(100), seller NVARCHAR(100),
    buyer_agent NVARCHAR(100), seller_agent NVARCHAR(100),
    offer_price DECIMAL(14,2), proposed_cap_rate DECIMAL(5,2), list_price DECIMAL(14,2),
    days_on_market INT, loa_date DATE, due_diligence_deadline DATE, closing_target_date DATE,
    commission_percentage DECIMAL(5,2), commission_total DECIMAL(12,2),
    status NVARCHAR(20) DEFAULT 'Active', notes NVARCHAR(MAX),
    created_at DATETIME DEFAULT GETDATE(), updated_at DATETIME DEFAULT GETDATE()
)
""")
cursor.execute("""
IF EXISTS (SELECT 1 FROM sys.tables WHERE name = 'activities')
   AND NOT EXISTS (
       SELECT 1 FROM sys.columns
       WHERE object_id = OBJECT_ID('activities') AND name = 'activity_type'
   )
DROP TABLE activities
""")
cursor.execute("""
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'activities')
CREATE TABLE activities (
    id INT IDENTITY(1,1) PRIMARY KEY,
    deal_id INT, contact_id INT, activity_type NVARCHAR(50), subject NVARCHAR(200),
    description NVARCHAR(MAX), due_date DATE, completed_at DATETIME,
    assigned_to NVARCHAR(100), status NVARCHAR(20) DEFAULT 'Open',
    created_at DATETIME DEFAULT GETDATE()
)
""")
cursor.execute("""
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'units')
CREATE TABLE units (
    id INT IDENTITY(1,1) PRIMARY KEY,
    property_id INT NOT NULL,
    unit_number NVARCHAR(20) NOT NULL,
    floor_plan NVARCHAR(50),
    beds INT,
    baths DECIMAL(3,1),
    square_feet INT,
    market_rent DECIMAL(10,2),
    status NVARCHAR(20) DEFAULT 'Occupied',
    created_at DATETIME DEFAULT GETDATE(),
    updated_at DATETIME DEFAULT GETDATE()
)
""")
cursor.execute("""
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'residents')
CREATE TABLE residents (
    id INT IDENTITY(1,1) PRIMARY KEY,
    first_name NVARCHAR(50) NOT NULL,
    last_name NVARCHAR(50) NOT NULL,
    email NVARCHAR(120),
    phone NVARCHAR(30),
    status NVARCHAR(20) DEFAULT 'Active',
    credit_band NVARCHAR(20),
    created_at DATETIME DEFAULT GETDATE()
)
""")
cursor.execute("""
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'leases')
CREATE TABLE leases (
    id INT IDENTITY(1,1) PRIMARY KEY,
    property_id INT NOT NULL,
    unit_id INT NOT NULL,
    resident_id INT NOT NULL,
    lease_start DATE NOT NULL,
    lease_end DATE NOT NULL,
    monthly_rent DECIMAL(10,2) NOT NULL,
    security_deposit DECIMAL(10,2),
    lease_status NVARCHAR(30) DEFAULT 'Current',
    renewal_offer_sent BIT DEFAULT 0,
    created_at DATETIME DEFAULT GETDATE(),
    updated_at DATETIME DEFAULT GETDATE()
)
""")
cursor.execute("""
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'work_orders')
CREATE TABLE work_orders (
    id INT IDENTITY(1,1) PRIMARY KEY,
    property_id INT NOT NULL,
    unit_id INT NULL,
    resident_id INT NULL,
    category NVARCHAR(50),
    priority NVARCHAR(20) DEFAULT 'Medium',
    status NVARCHAR(20) DEFAULT 'Open',
    description NVARCHAR(400),
    submitted_at DATETIME DEFAULT GETDATE(),
    completed_at DATETIME NULL,
    assigned_vendor NVARCHAR(100),
    estimated_cost DECIMAL(10,2),
    actual_cost DECIMAL(10,2)
)
""")
cursor.execute("""
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'charges')
CREATE TABLE charges (
    id INT IDENTITY(1,1) PRIMARY KEY,
    lease_id INT NOT NULL,
    charge_month DATE NOT NULL,
    charge_type NVARCHAR(30) DEFAULT 'Rent',
    amount DECIMAL(10,2) NOT NULL,
    payment_status NVARCHAR(20) DEFAULT 'Pending',
    paid_at DATETIME NULL,
    created_at DATETIME DEFAULT GETDATE()
)
""")
cursor.execute("""
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'r1_sites')
CREATE TABLE r1_sites (
    id INT IDENTITY(1,1) PRIMARY KEY,
    site_code NVARCHAR(30) NOT NULL,
    site_name NVARCHAR(120) NOT NULL,
    city NVARCHAR(60) NOT NULL,
    state NVARCHAR(30) NOT NULL,
    region NVARCHAR(40) NOT NULL,
    opened_on DATE NOT NULL,
    portfolio NVARCHAR(80) NOT NULL,
    status NVARCHAR(30) DEFAULT 'Active',
    created_at DATETIME2 DEFAULT SYSUTCDATETIME()
)
""")
cursor.execute("""
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'r1_devices')
CREATE TABLE r1_devices (
    id INT IDENTITY(1,1) PRIMARY KEY,
    site_id INT NOT NULL,
    device_serial NVARCHAR(50) NOT NULL,
    device_name NVARCHAR(120) NOT NULL,
    model NVARCHAR(50) NOT NULL,
    firmware_version NVARCHAR(30) NOT NULL,
    zone NVARCHAR(50) NOT NULL,
    installed_on DATE NOT NULL,
    status NVARCHAR(30) DEFAULT 'Online',
    vendor NVARCHAR(40) DEFAULT 'Ruckus',
    created_at DATETIME2 DEFAULT SYSUTCDATETIME()
)
""")
cursor.execute("""
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'r1_device_events')
CREATE TABLE r1_device_events (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    site_id INT NOT NULL,
    device_id INT NOT NULL,
    event_ts DATETIME2 NOT NULL,
    severity NVARCHAR(20) NOT NULL,
    event_type NVARCHAR(50) NOT NULL,
    summary NVARCHAR(300) NOT NULL,
    is_open BIT DEFAULT 0,
    created_at DATETIME2 DEFAULT SYSUTCDATETIME()
)
""")
cursor.execute("""
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'r1_device_daily_metrics')
CREATE TABLE r1_device_daily_metrics (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    device_id INT NOT NULL,
    metric_date DATE NOT NULL,
    uptime_pct DECIMAL(5,2) NOT NULL,
    throughput_mbps DECIMAL(10,2) NOT NULL,
    latency_ms DECIMAL(8,2) NOT NULL,
    packet_loss_pct DECIMAL(5,2) NOT NULL,
    client_sessions INT NOT NULL,
    incidents INT NOT NULL,
    created_at DATETIME2 DEFAULT SYSUTCDATETIME()
)
""")
conn.commit()
print("Tables ready.")


def insert_batch(table, columns, rows, target):
    if isinstance(columns, str):
        col_list = [c.strip() for c in columns.split(",") if c.strip()]
    else:
        col_list = list(columns)

    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    existing = cursor.fetchone()[0]
    if existing >= target:
        print(f"  {table}: {existing} records (target {target}) — skipping")
        return
    to_insert = rows[:target - existing]
    placeholders = ",".join("?" for _ in col_list)
    for idx in range(0, len(to_insert), 1000):
        chunk = to_insert[idx:idx + 1000]
        cursor.executemany(
            f"INSERT INTO {table} ({','.join(col_list)}) VALUES ({placeholders})",
            chunk,
        )
    conn.commit()
    print(f"  {table}: inserted {len(to_insert)} (now {existing + len(to_insert)}/{target})")


# ─── Properties ───────────────────────────────────────────────────────

PROPERTIES = [
    # Original 8
    ("The Vue at Madison", "123 Madison Ave", "Memphis", "TN", "38103", "Multifamily", 240, 2018, 210000, 3.2, 228, 1625, 1872000, 5.8, 32275862, "Madison Street Partners", "Pinnacle Property Management", "Active",
     '["Pool","Fitness Center","Rooftop Lounge","Covered Parking","Pet Park","Smart Locks"]',
     "Class A asset in booming downtown Memphis. Walking distance to Beale Street. 95% occupied consistently."),
    ("Riverside Heights", "800 Riverside Blvd", "Memphis", "TN", "38103", "Multifamily", 180, 2015, 158000, 2.8, 171, 1475, 1380000, 5.5, 25090909, "Riverside Capital Group", "Greystar Management", "Active",
     '["Pool","Fitness Center","River Views","Business Center","Bike Storage"]',
     "Harbor Town location with Mississippi River views. Premium unit mix with 30% townhomes."),
    ("Oakwood Crossings", "4525 Oakwood Dr", "Memphis", "TN", "38117", "Multifamily", 96, 1985, 72000, 5.1, 82, 1095, 648000, 6.2, 10451613, "Oakwood Holdings LLC", "Self-managed", "Active",
     '["Laundry","Off-Street Parking","Storage Units"]',
     "Value-add opportunity in East Memphis. Recently renovated 40% of units. Stable occupancy with upside on rents."),
    ("Highland Ridge", "3200 Highland Ave", "Memphis", "TN", "38111", "Multifamily", 64, 1978, 48000, 3.5, 58, 975, 384000, 6.8, 5647059, "Highland Properties LLC", "Self-managed", "Active",
     '["Laundry","Off-Street Parking","Grill Area"]',
     "Near University of Memphis. Strong student/graduate tenant base. 90% occupied with 5% rent growth YoY."),
    ("The Emerson", "150 Court Ave", "Memphis", "TN", "38103", "Multifamily", 312, 2021, 285000, 1.8, 296, 1895, 3450000, 5.2, 66346154, "Emerson Development Group", "Cushman & Wakefield", "Active",
     '["Pool","Fitness Center","Concierge","Valet Parking","Rooftop Pool","Dog Spa","Co-Working"]',
     "Downtown's premier luxury high-rise. Opened 2021 at 92% pre-leased. Top-of-market rents with premium finishes."),
    ("Southgate Village", "782 South Parkway E", "Memphis", "TN", "38106", "Multifamily", 128, 1972, 86000, 4.2, 102, 845, 480000, 7.5, 6400000, "Southgate REIT", "FirstService Residential", "Active",
     '["Laundry","Off-Street Parking","Community Room","Playground"]',
     "Workforce housing in South Memphis. Stable cash-flow asset with 98% occupancy. Section 8 vouchers accepted."),
    ("Poplar Pointe", "6280 Poplar Ave", "Memphis", "TN", "38119", "Multifamily", 72, 1998, 54000, 2.1, 68, 1280, 560000, 5.9, 9491525, "Poplar Pointe Investors", "Mid-South Property Group", "Active",
     '["Pool","Fitness Center","Garage Parking","Elevator"]',
     "East Memphis mid-rise near Regalia. Professional tenant base, mostly young professionals. Recently renovated lobby and common areas."),
    ("Village at Germantown", "9122 Exeter Rd", "Germantown", "TN", "38138", "Multifamily", 156, 2005, 130000, 6.8, 148, 1475, 1248000, 5.4, 23111111, "Germantown Development LLC", "BH Management", "Under Contract",
     '["Pool","Tennis Courts","Fitness Center","Clubhouse","Covered Parking","Walking Trails"]',
     "Top-tier Germantown location. Excellent schools nearby. Under contract — closing Q3 2026."),
    # New: 4 more
    ("University Village", "3500 Alumni Ave", "Memphis", "TN", "38152", "Student Housing", 120, 1975, 72000, 4.8, 112, 725, 396000, 7.0, 5657143, "U of M Properties LLC", "Campus Living Solutions", "Active",
     '["Laundry","Furnished Units","Study Lounge","Bike Storage","Grill Area"]',
     "Student housing adjacent to University of Memphis campus. 93% occupancy. Per-bed leasing model. Strong renewal rate of 62%."),
    ("The Gardens at Shelby", "7800 Poplar Pike", "Memphis", "TN", "38125", "Senior Living", 90, 2008, 68000, 3.2, 86, 2100, 856000, 6.5, 13169231, "Shelby Senior Housing Fund", "Legacy Senior Living", "Active",
     '["Elevator","Community Dining","Activity Center","Transportation","Emergency Call System","Garden"]',
     "Independent senior living in East Memphis. 95% occupied. Waitlist for 1BR units. Restaurant-style dining and weekly activities."),
    ("Court Square Flats", "10 N Main St", "Memphis", "TN", "38103", "Mixed-Use", 24, 1920, 28000, 0.3, 22, 1550, 186000, 5.5, 3381818, "Court Square Development LLC", "Downtown Property Group", "Active",
     '["Historic Building","Retail Below","Rooftop Deck","Laundry","Storage"]',
     "Boutique mixed-use building in historic Court Square. 24 luxury loft apartments above retail. 1920s character with modern finishes. 92% occupied."),
    ("Cordova Station", "1050 N Germantown Pkwy", "Cordova", "TN", "38018", "Multifamily", 168, 2001, 125000, 7.5, 154, 1185, 1008000, 5.8, 17379310, "Cordova Station Partners", "RPM Management", "Active",
     '["Pool","Fitness Center","Clubhouse","Playground","Walking Trails","Garage Parking"]',
     "Garden-style suburban asset in growing Cordova submarket. 92% occupied. Family-oriented with good schools. Stable cash flow with 3% annual rent growth."),
]
insert_batch("properties", "name,address,city,state,zip,property_type,total_units,year_built,building_size_sqft,lot_size_acres,units_occupied,average_rent,noi,cap_rate,estimated_value,owner,property_manager,status,amenities,notes", PROPERTIES, TARGET_PROPERTIES)

# ─── Contacts ─────────────────────────────────────────────────────────

CONTACTS = [
    # Original 12
    ("Robert", "Henderson", "rhenderson@madisonstreet.com", "901-555-0101", "Madison Street Partners", "Managing Partner", "Owner", 1, "Acquired The Vue in 2019. Looking to expand portfolio in downtown Memphis."),
    ("Sarah", "Mitchell", "smitchell@greystar.com", "901-555-0102", "Greystar Management", "Senior Property Manager", "Property Manager", 2, "Oversees Riverside Heights portfolio. 15 years MF experience."),
    ("James", "Campbell", "jcampbell@oakwoodholdings.com", "901-555-0103", "Oakwood Holdings LLC", "Principal", "Owner", 3, "Small-balance investor with 4 properties in Memphis. Active buyer for value-add deals."),
    ("Linda", "Thornton", "lthornton@cushwake.com", "901-555-0104", "Cushman & Wakefield", "Managing Director", "Broker", 5, "Top-producing MF broker in Memphis. $120M+ in transactions last 12 months."),
    ("Michael", "Davidson", "mdavidson@southgatereit.com", "901-555-0105", "Southgate REIT", "VP of Acquisitions", "Investor", 6, "REIT targeting workforce housing in secondary markets. $50M annual acquisition budget."),
    ("Patricia", "Wong", "pwong@emersongroup.com", "901-555-0106", "Emerson Development Group", "CEO", "Owner", 5, "Developer of The Emerson. Currently scoping next downtown project."),
    ("David", "Reynolds", "dreynolds@poplarpointe.com", "901-555-0107", "Poplar Pointe Investors", "General Partner", "Owner", 7, "Syndicator focused on East Memphis. Raised $4.2M for Poplar Pointe acquisition."),
    ("Amanda", "Foster", "afoster@bhmanagement.com", "901-555-0108", "BH Management", "Regional Director", "Property Manager", 8, "Manages 5 properties in the Mid-South region. 20 years experience."),
    ("Thomas", "Garrett", "tgarrett@transwestern.com", "901-555-0109", "Transwestern", "Senior Director", "Broker", None, "Specializes in investment sales. Currently marketing 3 MF assets in TN."),
    ("Jennifer", "Coleman", "jcoleman@firstservice.com", "901-555-0110", "FirstService Residential", "Portfolio Manager", "Property Manager", 6, "Manages Southgate and 2 other workforce housing properties."),
    ("Marcus", "Williams", "mwilliams@highlandprop.com", "901-555-0111", "Highland Properties LLC", "Owner/Operator", "Owner", 4, "Small owner-operator. Owns Highland Ridge and one other property near U of M."),
    ("Angela", "Price", "aprice@meridiancap.com", "901-555-0112", "Meridian Capital Group", "Senior Analyst", "Lender", None, "Debt placement specialist. Arranged financing for 3 MF deals in 2025 ($28M total)."),
    # New: 8 more
    ("Brian", "Foster", "bfoster@firsthorizon.com", "901-555-0113", "First Horizon Bank", "VP Commercial Lending", "Lender", None, "Primary lender for 4 of our portfolio properties. $45M in active MF loans. Aggressive on rates for Class A."),
    ("Karen", "Sims", "ksims@adamsreese.com", "901-555-0114", "Adams & Reese LLP", "Partner", "Attorney", None, "Real estate transactions and due diligence counsel. Handled all 3 Q1-Q2 closings."),
    ("Derek", "Jackson", "djackson@cbrevaluation.com", "901-555-0115", "CBRE Valuation", "Senior Appraiser", "Appraiser", None, "Lead appraiser for Memphis MF market. 20+ years experience. Knows the submarkets inside and out."),
    ("Maria", "Gonzalez", "mgonzalez@gonzalezconstruction.com", "901-555-0116", "Gonzalez Construction", "President", "Contractor", None, "Preferred GC for value-add renovations. Completed 4 property renovations in 2025. $12M annual revenue."),
    ("Steven", "Cole", "scole@regions.com", "901-555-0117", "Regions Bank", "SVP Commercial Real Estate", "Lender", None, "Opened $32M credit facility for Emerson acquisition. Relationship banker for 5 MF owners."),
    ("Rachel", "Bennett", "rbennett@harborgroup.com", "901-555-0118", "Harbor Group International", "Director of Acquisitions", "Investor", None, "HGI actively seeking Memphis MF acquisitions. Target: $20-75M, Class A, downtown/suburban. $500M dry powder allocated."),
    ("Chris", "Walker", "cwalker@walkerinspections.com", "901-555-0119", "Walker Property Inspections", "Owner", "Inspector", None, "Licensed home inspector. Performed all Phase I and property condition assessments for our listings. 1,200+ inspections."),
    ("Jonathan", "Reed", "jreed@jll.com", "901-555-0120", "JLL Capital Markets", "Managing Director", "Broker", None, "Competing broker for institutional MF mandates. Known Blackstone and Invesco relationships. Co-broke The Emerson with Linda."),
]
insert_batch("contacts", "first_name,last_name,email,phone,company,job_title,role,property_id,notes", CONTACTS, TARGET_CONTACTS)

# ─── Deals ─────────────────────────────────────────────────────────────

DEALS = [
    # Original 8
    (8, "Sale", "Closing", "Warburg Realty Trust", "Germantown Development LLC", "Linda Thornton", "Thomas Garrett", 24500000, 5.25, 25800000, 42, "2026-03-15", "2026-05-01", "2026-07-15", 3.0, 735000, "Active", "Full commission at 3%. Both sides represented. Title work underway."),
    (1, "Sale", "Due Diligence", "Blackstone Real Estate", "Madison Street Partners", "Linda Thornton", "Thomas Garrett", 34000000, 5.5, 35800000, 28, "2026-04-10", "2026-06-15", "2026-08-30", 2.5, 850000, "Active", "Largest deal in pipeline. Buyer doing extensive Phase I and structural inspection."),
    (3, "Sale", "LOI", "ValueAdd Equity Fund III", "Oakwood Holdings LLC", "Michael Davidson", "Linda Thornton", 11500000, 6.0, 12500000, 14, "2026-05-01", "2026-06-30", "2026-09-15", 3.0, 345000, "Active", "LOI signed. Buyer touring next week. Value-add play with renovation plan."),
    (5, "Sale", "LOI", "Invesco Real Estate", "Emerson Development Group", "Linda Thornton", "Thomas Garrett", 68000000, 5.0, 72000000, 21, "2026-04-28", "2026-07-01", "2026-10-01", 2.0, 1360000, "Active", "Marquee downtown asset. Multiple offers received. Negotiating final terms."),
    (4, "Sale", "Underwriting", "Camber Property Group", "Highland Properties LLC", "Linda Thornton", "Thomas Garrett", 6200000, 6.5, 6800000, 18, "2026-05-10", "2026-07-15", "2026-10-30", 3.5, 217000, "Active", "Investor pursuing 1031 exchange. Underwriting in progress."),
    (2, "Sale", "Closed", "Warburg Realty Trust", "Riverside Capital Group", "Linda Thornton", "Thomas Garrett", 26500000, 5.3, 27500000, 35, "2026-01-15", "2026-03-01", "2026-05-01", 2.5, 662500, "Closed", "Closed May 1, 2026. Smooth transaction. Buyer assumed existing management."),
    (7, "Sale", "Closed", "Poplar Pointe Investors", "Private Seller", "Linda Thornton", "Thomas Garrett", 9800000, 5.8, 10200000, 28, "2026-02-01", "2026-03-20", "2026-05-15", 3.0, 294000, "Closed", "Closed May 15. Syndication deal with 12 LP investors. Exceeded fundraising target."),
    (6, "Sale", "Lost", "N/A", "Southgate REIT", "Michael Davidson", "Thomas Garrett", 6800000, 7.2, 7200000, 45, "2025-12-01", "2026-02-01", None, 2.5, 170000, "Lost", "REIT decided to hold. Capital allocation shifted to Southeast market."),
    # New: 4 more
    (10, "Lease", "Negotiating", "Shelby Senior Housing Fund", "Trustee of Shelby County", "Linda Thornton", "Jonathan Reed", 850000, 6.25, 920000, 35, "2026-04-20", "2026-06-15", "2026-08-01", 4.0, 34000, "Active", "Ground lease renewal for The Gardens at Shelby. 99-year lease with 2% annual escalator. County commission approval pending."),
    (5, "Refinance", "Underwriting", "N/A", "Emerson Development Group", "Linda Thornton", "N/A", 45000000, None, 45000000, 0, "2026-05-05", "2026-07-01", "2026-08-15", 0.5, 225000, "Active", "Refinancing The Emerson. Current loan maturing Oct 2026. New 10-year fixed at 5.25%. Pat Wong exploring cash-out refi for next project."),
    (None, "Sale", "LOI", "Pinnacle Development Group", "Germantown Land Trust", "Thomas Garrett", "Linda Thornton", 3200000, None, 3800000, 60, "2026-05-12", "2026-07-15", "2026-10-01", 3.5, 112000, "Active", "8.2-acre development parcel on Germantown Rd. Entitled for 120-unit MF. Seller motivated — carrying cost high."),
    (None, "Sale", "LOI", "BlueSky Capital Partners", "Various Sellers", "Linda Thornton", "Thomas Garrett", 14500000, 7.0, 16000000, 14, "2026-05-18", "2026-07-01", "2026-09-30", 2.5, 362500, "Active", "Two-property portfolio: Southgate Village + Highland Ridge. Combined 192 units, $864K NOI. Buyer pursuing portfolio discount."),
]
insert_batch("deals", "property_id,deal_type,stage,buyer,seller,buyer_agent,seller_agent,offer_price,proposed_cap_rate,list_price,days_on_market,loa_date,due_diligence_deadline,closing_target_date,commission_percentage,commission_total,status,notes", DEALS, TARGET_DEALS)

# ─── Activities ────────────────────────────────────────────────────────

ACTIVITIES = [
    # Original 14
    (1, None, "Tour", "Property tour with Blackstone team", "Full walkthrough of The Vue. Inspecting unit finishes, common areas, and mechanicals.", "2026-04-12", "2026-04-12T14:30:00", "Linda Thornton", "Completed"),
    (3, None, "Tour", "ValueAdd Equity tour of Oakwood Crossings", "Buyer team touring property. Focus on recently renovated units and deferred maintenance.", "2026-05-15", None, "Linda Thornton", "Open"),
    (4, None, "Tour", "Camber Group tour Highland Ridge", "Initial tour with Camber's acquisitions team. Discussing value-add potential near U of M.", "2026-05-20", None, "Linda Thornton", "Open"),
    (2, None, "Inspection", "Phase I Environmental — The Vue", "Buyer-ordered Phase I environmental assessment. Reports due by June 1.", "2026-05-25", None, "Environmental Partners Inc", "Open"),
    (2, None, "Inspection", "Structural engineering review", "Review of 2018 construction quality. Engineer flagged roof warranty concern.", "2026-05-20", None, "Southeastern Engineering", "Open"),
    (1, None, "Inspection", "Final walkthrough — Village at Germantown", "Pre-closing walkthrough with Warburg team. Punch list items to be addressed before July 1.", "2026-06-30", None, "Linda Thornton", "Open"),
    (3, 3, "Call", "Price negotiation call — Oakwood Crossings", "James Campbell pushing for $12M. Buyer at $11M. Need to find middle ground.", "2026-05-18", "2026-05-18T10:00:00", "Linda Thornton", "Completed"),
    (2, 1, "Meeting", "Property tour debrief with Robert Henderson", "Robert wants to discuss 1031 options post-sale. Potential buyer for his next acquisition.", "2026-04-14", "2026-04-14T11:00:00", "Linda Thornton", "Completed"),
    (4, 6, "Meeting", "Listing strategy for The Emerson", "Discussing off-market vs. public listing strategy. Current LOI in play but want backup offers.", "2026-05-10", None, "Linda Thornton", "Open"),
    (8, None, "Appraisal", "Appraisal — Village at Germantown", "Lender-ordered appraisal. Expected value range $24-26M.", "2026-06-01", None, "Memphis Appraisal Group", "Open"),
    (2, None, "Appraisal", "Appraisal — The Vue", "Buyer's lender requiring full appraisal. Comparable sales in downtown Memphis.", "2026-06-10", None, "CBRE Valuation", "Open"),
    (None, 2, "Call", "Quarterly check-in — Riverside Heights", "Sarah reporting 96% occupancy. Discussing upcoming rent increases for July renewals.", "2026-05-12", "2026-05-12T09:00:00", "Linda Thornton", "Completed"),
    (None, 4, "Meeting", "Q2 business review with Linda", "Reviewing Q2 pipeline ($88M total), closed deals ($12.7M), and Q3 forecasting.", "2026-05-22", None, "Linda Thornton", "Open"),
    (6, 5, "Call", "Re-engagement call — Southgate REIT", "Michael mentioned they may reconsider sale in Q4. Keep in touch for off-market opportunity.", "2026-05-08", "2026-05-08T15:00:00", "Linda Thornton", "Completed"),
    # New: 10 more
    (9, 13, "Meeting", "Lender lunch — First Horizon credit review", "Meeting Brian Foster to discuss First Horizon's 2027 MF lending appetite. Rates expected to drop 50bp.", "2026-05-28", None, "Linda Thornton", "Open"),
    (None, 14, "Call", "Attorney consult — closing docs review", "Karen Sims reviewing updated commission agreements and closing disclosure requirements.", "2026-05-16", "2026-05-16T11:30:00", "Linda Thornton", "Completed"),
    (12, 18, "Tour", "BlueSky Capital portfolio tour", "Walking Southgate Village and Highland Ridge with BlueSky's acquisitions team. Both properties in one day.", "2026-06-05", None, "Linda Thornton", "Open"),
    (None, 15, "Inspection", "Derek Jackson — The Vue appraisal walk", "Accompanying Derek for the appraisal inspection. Providing comps and financial data.", "2026-06-08", None, "Linda Thornton", "Open"),
    (10, 12, "Appraisal", "Refinance appraisal — The Emerson", "Lender-ordered appraisal for $45M refinance. Coordinating access to all 312 units for inspection.", "2026-06-15", None, "Memphis Appraisal Group", "Open"),
    (3, 17, "Call", "Contractor bid review — Oakwood renovations", "Maria Gonzalez submitting renovation bid for 60 unrenovated units at Oakwood. $1.2M estimated scope.", "2026-05-25", None, "Linda Thornton", "Open"),
    (None, 19, "Meeting", "New business lunch — JLL collaboration", "Jonathan Reed wants to discuss co-broke opportunities on future Germantown listings.", "2026-06-02", None, "Linda Thornton", "Open"),
    (11, None, "Meeting", "Germantown land parcel — Pinnacle negotiation", "Meeting with Pinnacle Development to negotiate $3.2M offer on 8.2-acre development site.", "2026-05-30", None, "Thomas Garrett", "Open"),
    (None, None, "Tour", "Rachel Bennett — Harbor Group property tour", "Harbor Group's Director of Acquisitions in town. Touring The Emerson and The Vue. High-priority prospect.", "2026-06-12", None, "Linda Thornton", "Open"),
    (None, 4, "Meeting", "Weekly deal pipeline review", "Standard Monday pipeline review. 12 active deals, $197M total pipeline. Reviewing Q3 targets.", "2026-05-19", "2026-05-19T09:00:00", "Linda Thornton", "Completed"),
]
insert_batch("activities", "deal_id,contact_id,activity_type,subject,description,due_date,completed_at,assigned_to,status", ACTIVITIES, TARGET_ACTIVITIES)

# ─── Property Operations (Entrata/Yardi-style, synthetic) ───────────

UNITS = [
    (1, "A-101", "1BR-A", 1, 1.0, 735, 1545, "Occupied"),
    (1, "A-203", "2BR-B", 2, 2.0, 1060, 1895, "Occupied"),
    (1, "B-305", "2BR-A", 2, 2.0, 990, 1810, "Vacant"),
    (2, "R-110", "1BR-A", 1, 1.0, 710, 1425, "Occupied"),
    (2, "R-214", "2BR-A", 2, 2.0, 1025, 1710, "Occupied"),
    (2, "R-318", "3BR-A", 3, 2.0, 1280, 2075, "Notice"),
    (3, "O-01", "1BR-Classic", 1, 1.0, 640, 995, "Occupied"),
    (3, "O-12", "2BR-Reno", 2, 1.5, 910, 1210, "Occupied"),
    (3, "O-22", "2BR-Classic", 2, 1.5, 890, 1150, "Vacant"),
    (4, "H-06", "1BR-A", 1, 1.0, 590, 915, "Occupied"),
    (4, "H-16", "2BR-A", 2, 1.5, 860, 1125, "Occupied"),
    (5, "E-1012", "1BR-Lux", 1, 1.0, 805, 2050, "Occupied"),
    (5, "E-1411", "2BR-Lux", 2, 2.0, 1190, 2760, "Occupied"),
    (5, "E-1804", "3BR-Penthouse", 3, 2.5, 1675, 3980, "Occupied"),
    (6, "S-04", "1BR-Workforce", 1, 1.0, 600, 825, "Occupied"),
    (6, "S-21", "2BR-Workforce", 2, 1.0, 820, 980, "Delinquent"),
    (7, "P-17", "1BR-A", 1, 1.0, 700, 1230, "Occupied"),
    (7, "P-38", "2BR-A", 2, 2.0, 980, 1510, "Occupied"),
    (8, "G-102", "1BR-Premium", 1, 1.0, 760, 1450, "Occupied"),
    (8, "G-223", "2BR-Premium", 2, 2.0, 1105, 1780, "Occupied"),
    (9, "U-09", "PerBed-4x4", 4, 4.0, 1360, 2900, "Occupied"),
    (10, "GS-14", "1BR-Senior", 1, 1.0, 680, 2090, "Occupied"),
    (11, "CS-4B", "Loft-1BR", 1, 1.0, 810, 1625, "Occupied"),
    (12, "C-27", "2BR-Garden", 2, 2.0, 1035, 1285, "Occupied"),
]
insert_batch("units", "property_id,unit_number,floor_plan,beds,baths,square_feet,market_rent,status", UNITS, TARGET_UNITS)

RESIDENTS = [
    ("Alex", "Morgan", "alex.morgan@example.com", "901-555-1001", "Active", "A"),
    ("Priya", "Shah", "priya.shah@example.com", "901-555-1002", "Active", "A"),
    ("Jordan", "Lee", "jordan.lee@example.com", "901-555-1003", "Active", "B"),
    ("Taylor", "Brooks", "taylor.brooks@example.com", "901-555-1004", "Active", "B"),
    ("Casey", "Nguyen", "casey.nguyen@example.com", "901-555-1005", "Active", "A"),
    ("Riley", "Hughes", "riley.hughes@example.com", "901-555-1006", "Notice", "B"),
    ("Morgan", "Diaz", "morgan.diaz@example.com", "901-555-1007", "Active", "C"),
    ("Avery", "Patel", "avery.patel@example.com", "901-555-1008", "Active", "B"),
    ("Sam", "Parker", "sam.parker@example.com", "901-555-1009", "Active", "A"),
    ("Jamie", "Reed", "jamie.reed@example.com", "901-555-1010", "Active", "A"),
    ("Cameron", "Bell", "cameron.bell@example.com", "901-555-1011", "Active", "B"),
    ("Reese", "Gomez", "reese.gomez@example.com", "901-555-1012", "Delinquent", "C"),
    ("Peyton", "Carter", "peyton.carter@example.com", "901-555-1013", "Active", "A"),
    ("Drew", "Ward", "drew.ward@example.com", "901-555-1014", "Active", "B"),
    ("Quinn", "Fisher", "quinn.fisher@example.com", "901-555-1015", "Active", "B"),
    ("Blake", "West", "blake.west@example.com", "901-555-1016", "Active", "A"),
    ("Skyler", "Howard", "skyler.howard@example.com", "901-555-1017", "Active", "B"),
    ("Logan", "Barnes", "logan.barnes@example.com", "901-555-1018", "Active", "A"),
]
insert_batch("residents", "first_name,last_name,email,phone,status,credit_band", RESIDENTS, TARGET_RESIDENTS)

LEASES = [
    (1, 1, 1, "2025-08-01", "2026-07-31", 1545, 750, "Current", 1),
    (1, 2, 2, "2025-10-01", "2026-09-30", 1895, 1000, "Current", 1),
    (2, 4, 3, "2025-09-15", "2026-09-14", 1425, 700, "Current", 0),
    (2, 5, 4, "2025-12-01", "2026-11-30", 1710, 900, "Current", 0),
    (2, 6, 5, "2025-06-01", "2026-05-31", 2075, 1200, "Renewal", 1),
    (3, 7, 6, "2025-05-01", "2026-04-30", 995, 500, "Month-to-Month", 1),
    (3, 8, 7, "2025-07-01", "2026-06-30", 1210, 600, "Current", 0),
    (4, 10, 8, "2025-11-01", "2026-10-31", 915, 450, "Current", 0),
    (4, 11, 9, "2025-10-10", "2026-10-09", 1125, 550, "Current", 0),
    (5, 12, 10, "2026-01-01", "2026-12-31", 2050, 1000, "Current", 0),
    (5, 13, 11, "2025-09-01", "2026-08-31", 2760, 1500, "Current", 1),
    (5, 14, 12, "2025-07-01", "2026-06-30", 3980, 2500, "Current", 1),
    (6, 15, 13, "2025-08-01", "2026-07-31", 825, 400, "Current", 0),
    (6, 16, 14, "2025-03-01", "2026-02-28", 980, 450, "Delinquent", 1),
    (7, 17, 15, "2026-02-01", "2027-01-31", 1230, 600, "Current", 0),
    (8, 19, 16, "2025-09-01", "2026-08-31", 1450, 700, "Current", 1),
    (10, 22, 17, "2025-06-01", "2026-05-31", 2090, 1000, "Renewal", 1),
    (12, 24, 18, "2025-11-15", "2026-11-14", 1285, 650, "Current", 0),
]
insert_batch("leases", "property_id,unit_id,resident_id,lease_start,lease_end,monthly_rent,security_deposit,lease_status,renewal_offer_sent", LEASES, TARGET_LEASES)

WORK_ORDERS = [
    (1, 1, 1, "HVAC", "High", "Open", "AC not cooling in living room", "2026-05-20", None, "CoolAir Mechanical", 280, None),
    (1, 2, 2, "Appliance", "Medium", "Completed", "Dishwasher leaks during cycle", "2026-05-03", "2026-05-05T10:20:00", "QuickFix Appliance", 145, 132),
    (2, 4, 3, "Plumbing", "High", "Open", "Water pressure drop in shower", "2026-05-22", None, "Memphis Plumbing Co", 320, None),
    (2, 6, 5, "Electrical", "Medium", "Open", "Breaker trips when oven runs", "2026-05-18", None, "SparkPro Electric", 250, None),
    (3, 8, 7, "Make Ready", "High", "In Progress", "Turn unit for incoming lease", "2026-05-25", None, "In-house Turn Team", 1200, None),
    (3, 9, None, "Grounds", "Low", "Open", "Replace damaged exterior light", "2026-05-26", None, "Site Staff", 85, None),
    (4, 10, 8, "Pest", "Medium", "Completed", "Quarterly pest treatment", "2026-05-02", "2026-05-02T13:00:00", "SafeHome Pest", 95, 95),
    (4, 11, 9, "Plumbing", "High", "Open", "Kitchen sink backup", "2026-05-24", None, "Memphis Plumbing Co", 175, None),
    (5, 12, 10, "Access", "Low", "Completed", "Replace mailbox key", "2026-05-10", "2026-05-11T09:15:00", "Concierge Team", 35, 30),
    (5, 13, 11, "HVAC", "High", "In Progress", "Condenser vibration noise", "2026-05-21", None, "CoolAir Mechanical", 540, None),
    (5, 14, 12, "Amenity", "Medium", "Open", "Gym treadmill maintenance", "2026-05-19", None, "FitEquip Services", 260, None),
    (6, 16, 14, "Compliance", "High", "Open", "Balcony railing safety check", "2026-05-17", None, "CodeSafe Inspections", 190, None),
    (7, 17, 15, "Appliance", "Low", "Completed", "Replace garbage disposal", "2026-05-06", "2026-05-07T16:40:00", "QuickFix Appliance", 120, 118),
    (7, 18, None, "Turn", "Medium", "In Progress", "Carpet cleaning + repaint", "2026-05-23", None, "TurnRight Services", 680, None),
    (8, 19, 16, "Electrical", "Medium", "Open", "Entry light flickering", "2026-05-24", None, "SparkPro Electric", 110, None),
    (8, 20, None, "Grounds", "Low", "Completed", "Pool deck pressure wash", "2026-05-08", "2026-05-09T12:05:00", "BlueWave Maintenance", 220, 205),
    (10, 22, 17, "Safety", "High", "Open", "Install additional grab bars", "2026-05-18", None, "SeniorCare Retrofit", 340, None),
    (11, 23, None, "HVAC", "Medium", "Open", "Seasonal HVAC tune-up", "2026-05-27", None, "CoolAir Mechanical", 175, None),
    (12, 24, 18, "Plumbing", "Medium", "Completed", "Toilet tank replacement", "2026-05-09", "2026-05-10T14:00:00", "Memphis Plumbing Co", 140, 138),
    (12, None, None, "Grounds", "Low", "Open", "Parking lot striping touch-up", "2026-05-28", None, "LotMark Services", 950, None),
]
insert_batch("work_orders", "property_id,unit_id,resident_id,category,priority,status,description,submitted_at,completed_at,assigned_vendor,estimated_cost,actual_cost", WORK_ORDERS, TARGET_WORK_ORDERS)

CHARGES = [
    (1, "2026-05-01", "Rent", 1545, "Paid", "2026-05-02T09:10:00"),
    (1, "2026-06-01", "Rent", 1545, "Pending", None),
    (2, "2026-05-01", "Rent", 1895, "Paid", "2026-05-01T08:05:00"),
    (2, "2026-06-01", "Rent", 1895, "Pending", None),
    (3, "2026-05-01", "Rent", 1425, "Paid", "2026-05-03T14:22:00"),
    (3, "2026-05-01", "Utility", 95, "Paid", "2026-05-05T11:00:00"),
    (4, "2026-05-01", "Rent", 1710, "Paid", "2026-05-02T16:45:00"),
    (4, "2026-06-01", "Rent", 1710, "Pending", None),
    (5, "2026-05-01", "Rent", 2075, "Partial", "2026-05-04T10:12:00"),
    (5, "2026-05-01", "Pet", 35, "Paid", "2026-05-04T10:13:00"),
    (6, "2026-05-01", "Rent", 995, "Paid", "2026-05-06T09:40:00"),
    (6, "2026-06-01", "Rent", 995, "Pending", None),
    (7, "2026-05-01", "Rent", 1210, "Paid", "2026-05-05T13:01:00"),
    (7, "2026-05-01", "Fee", 50, "Paid", "2026-05-05T13:02:00"),
    (8, "2026-05-01", "Rent", 915, "Paid", "2026-05-02T09:20:00"),
    (8, "2026-06-01", "Rent", 915, "Pending", None),
    (9, "2026-05-01", "Rent", 1125, "Paid", "2026-05-01T15:30:00"),
    (9, "2026-05-01", "Utility", 110, "Pending", None),
    (10, "2026-05-01", "Rent", 2050, "Paid", "2026-05-03T08:45:00"),
    (10, "2026-06-01", "Rent", 2050, "Pending", None),
    (11, "2026-05-01", "Rent", 2760, "Paid", "2026-05-02T17:00:00"),
    (11, "2026-06-01", "Rent", 2760, "Pending", None),
    (12, "2026-05-01", "Rent", 3980, "Paid", "2026-05-02T09:55:00"),
    (12, "2026-05-01", "Parking", 175, "Paid", "2026-05-02T09:56:00"),
    (13, "2026-05-01", "Rent", 825, "Paid", "2026-05-05T16:02:00"),
    (13, "2026-06-01", "Rent", 825, "Pending", None),
    (14, "2026-05-01", "Rent", 980, "Delinquent", None),
    (14, "2026-05-01", "LateFee", 75, "Delinquent", None),
    (15, "2026-05-01", "Rent", 1230, "Paid", "2026-05-01T07:40:00"),
    (15, "2026-06-01", "Rent", 1230, "Pending", None),
    (16, "2026-05-01", "Rent", 1450, "Paid", "2026-05-03T12:20:00"),
    (16, "2026-05-01", "Utility", 88, "Paid", "2026-05-03T12:21:00"),
    (17, "2026-05-01", "Rent", 2090, "Paid", "2026-05-04T09:12:00"),
    (17, "2026-06-01", "Rent", 2090, "Pending", None),
    (18, "2026-05-01", "Rent", 1285, "Paid", "2026-05-06T14:10:00"),
    (18, "2026-06-01", "Rent", 1285, "Pending", None),
]
insert_batch("charges", "lease_id,charge_month,charge_type,amount,payment_status,paid_at", CHARGES, TARGET_CHARGES)

# ─── Ruckus R1 Operational History (synthetic, high volume) ─────────

R1_SITES = [
    ("R1-MEM-DT", "R1 Downtown Memphis Hub", "Memphis", "TN", "South", "2019-03-15", "Core Urban", "Active"),
    ("R1-MEM-EA", "R1 East Memphis Exchange", "Memphis", "TN", "South", "2020-06-10", "Core Urban", "Active"),
    ("R1-MEM-MID", "R1 Midtown Operations", "Memphis", "TN", "South", "2021-01-22", "Regional Core", "Active"),
    ("R1-GTN-N", "R1 Germantown North", "Germantown", "TN", "South", "2018-11-05", "Suburban Growth", "Active"),
    ("R1-CDV-W", "R1 Cordova West", "Cordova", "TN", "South", "2019-08-28", "Suburban Growth", "Active"),
    ("R1-NAS-CEN", "R1 Nashville Central", "Nashville", "TN", "Mid-South", "2017-05-09", "Market Expansion", "Active"),
    ("R1-ATL-MID", "R1 Atlanta Midtown", "Atlanta", "GA", "Southeast", "2020-02-14", "Market Expansion", "Active"),
    ("R1-DAL-NT", "R1 Dallas NorthTech", "Dallas", "TX", "Southwest", "2021-09-30", "National Growth", "Active"),
]
insert_batch(
    "r1_sites",
    "site_code,site_name,city,state,region,opened_on,portfolio,status",
    R1_SITES,
    TARGET_R1_SITES,
)

cursor.execute("SELECT TOP (?) id, site_code FROM r1_sites ORDER BY id", TARGET_R1_SITES)
site_rows = cursor.fetchall()
site_map = {row[1]: row[0] for row in site_rows}

site_codes_ordered = [site[0] for site in R1_SITES]
models = ("R750", "R760", "T350", "H550")
zones = ("Lobby", "Amenities", "Hallway", "Parking", "Pool", "Office")
firmware_cycle = ("5.2.1", "5.2.2", "5.2.3", "5.2.4")

r1_devices: list[tuple[object, ...]] = []
for site_idx, site_code in enumerate(site_codes_ordered):
    site_id = site_map.get(site_code)
    if site_id is None:
        continue
    for dev_num in range(1, 13):
        r1_devices.append(
            (
                site_id,
                f"R1-{site_code}-{dev_num:03d}",
                f"{site_code}-AP-{dev_num:02d}",
                models[(dev_num + site_idx) % len(models)],
                firmware_cycle[(dev_num + 2 * site_idx) % len(firmware_cycle)],
                zones[(dev_num + site_idx) % len(zones)],
                (date(2022, 1, 1) + timedelta(days=site_idx * 45 + dev_num)).isoformat(),
                "Online" if dev_num % 7 else "Degraded",
                "Ruckus",
            )
        )

insert_batch(
    "r1_devices",
    "site_id,device_serial,device_name,model,firmware_version,zone,installed_on,status,vendor",
    r1_devices,
    TARGET_R1_DEVICES,
)

cursor.execute("SELECT TOP (?) id, site_id FROM r1_devices ORDER BY id", TARGET_R1_DEVICES)
device_rows = cursor.fetchall()

event_types = (
    "ClientReconnectSpike",
    "APChannelInterference",
    "FirmwareDrift",
    "PowerCycleDetected",
    "HighLatencyBurst",
)
severities = ("Low", "Medium", "High", "Critical")

r1_events: list[tuple[object, ...]] = []
for device_idx, row in enumerate(device_rows):
    device_id = int(row[0])
    site_id = int(row[1])
    for event_idx in range(125):
        event_date = date(2023, 1, 1) + timedelta(days=(event_idx * 7 + device_idx) % 1080)
        event_hour = (event_idx * 3 + device_idx) % 24
        severity = severities[(event_idx + device_idx) % len(severities)]
        event_type = event_types[(event_idx + 2 * device_idx) % len(event_types)]
        summary = f"{event_type} detected at {event_hour:02d}:00 UTC"
        is_open = 1 if event_idx % 11 == 0 else 0
        r1_events.append(
            (
                site_id,
                device_id,
                f"{event_date.isoformat()}T{event_hour:02d}:00:00",
                severity,
                event_type,
                summary,
                is_open,
            )
        )

insert_batch(
    "r1_device_events",
    "site_id,device_id,event_ts,severity,event_type,summary,is_open",
    r1_events,
    TARGET_R1_DEVICE_EVENTS,
)

r1_daily_metrics: list[tuple[object, ...]] = []
window_start = date(2023, 1, 1)
for device_idx, row in enumerate(device_rows):
    device_id = int(row[0])
    for day_idx in range(365):
        metric_date = window_start + timedelta(days=day_idx)
        uptime = 97.2 + ((device_idx + day_idx) % 28) * 0.1
        throughput = 210.0 + ((device_idx * 3 + day_idx) % 190)
        latency = 11.5 + ((device_idx + day_idx * 2) % 26) * 0.4
        packet_loss = 0.15 + ((device_idx + day_idx) % 14) * 0.05
        sessions = 180 + ((device_idx * 5 + day_idx * 7) % 460)
        incidents = (device_idx + day_idx) % 4
        r1_daily_metrics.append(
            (
                device_id,
                metric_date.isoformat(),
                round(min(uptime, 99.95), 2),
                round(throughput, 2),
                round(latency, 2),
                round(packet_loss, 2),
                sessions,
                incidents,
            )
        )

insert_batch(
    "r1_device_daily_metrics",
    "device_id,metric_date,uptime_pct,throughput_mbps,latency_ms,packet_loss_pct,client_sessions,incidents",
    r1_daily_metrics,
    TARGET_R1_DAILY_METRICS,
)

print("Seed complete.")
cursor.close()
conn.close()
