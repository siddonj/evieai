-- 002: Multifamily & Brokerage schema — replaces generic CRM tables
-- Applies:   mcp_servers/sql/migrations/002_multifamily_schema.up.sql
-- Reverts:   mcp_servers/sql/migrations/002_multifamily_schema.down.sql

-- Drop old generic CRM tables
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'contacts')
DROP TABLE contacts;
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'companies')
DROP TABLE companies;

-- Properties — multifamily assets
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'properties')
CREATE TABLE properties (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(100) NOT NULL,
    address NVARCHAR(200),
    city NVARCHAR(50),
    state NVARCHAR(20),
    zip NVARCHAR(10),
    property_type NVARCHAR(50) DEFAULT 'Multifamily',
    total_units INT,
    year_built INT,
    building_size_sqft DECIMAL(12,0),
    lot_size_acres DECIMAL(8,2),
    units_occupied INT,
    average_rent DECIMAL(8,2),
    noi DECIMAL(14,2),
    cap_rate DECIMAL(5,2),
    estimated_value DECIMAL(14,2),
    owner NVARCHAR(100),
    property_manager NVARCHAR(100),
    status NVARCHAR(50) DEFAULT 'Active',
    amenities NVARCHAR(MAX),
    notes NVARCHAR(MAX),
    created_at DATETIME DEFAULT GETDATE(),
    updated_at DATETIME DEFAULT GETDATE()
);

-- Contacts — owners, brokers, investors, PMs, vendors
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'contacts')
CREATE TABLE contacts (
    id INT IDENTITY(1,1) PRIMARY KEY,
    first_name NVARCHAR(50) NOT NULL,
    last_name NVARCHAR(50) NOT NULL,
    email NVARCHAR(100),
    phone NVARCHAR(30),
    company NVARCHAR(100),
    job_title NVARCHAR(100),
    role NVARCHAR(50) DEFAULT 'Owner',
    property_id INT,
    notes NVARCHAR(MAX),
    created_at DATETIME DEFAULT GETDATE()
);

-- Deals — brokerage pipeline (LOI → Due Diligence → Financing → Closing → Closed/Lost)
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'deals')
CREATE TABLE deals (
    id INT IDENTITY(1,1) PRIMARY KEY,
    property_id INT,
    deal_type NVARCHAR(50) DEFAULT 'Sale',
    stage NVARCHAR(50) DEFAULT 'LOI',
    buyer NVARCHAR(100),
    seller NVARCHAR(100),
    buyer_agent NVARCHAR(100),
    seller_agent NVARCHAR(100),
    offer_price DECIMAL(14,2),
    proposed_cap_rate DECIMAL(5,2),
    list_price DECIMAL(14,2),
    days_on_market INT,
    loa_date DATE,
    due_diligence_deadline DATE,
    closing_target_date DATE,
    commission_percentage DECIMAL(5,2),
    commission_total DECIMAL(12,2),
    status NVARCHAR(20) DEFAULT 'Active',
    notes NVARCHAR(MAX),
    created_at DATETIME DEFAULT GETDATE(),
    updated_at DATETIME DEFAULT GETDATE()
);

-- Activities — tours, showings, calls, inspections tied to deals/contacts
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'activities')
CREATE TABLE activities (
    id INT IDENTITY(1,1) PRIMARY KEY,
    deal_id INT,
    contact_id INT,
    activity_type NVARCHAR(50),
    subject NVARCHAR(200),
    description NVARCHAR(MAX),
    due_date DATE,
    completed_at DATETIME,
    assigned_to NVARCHAR(100),
    status NVARCHAR(20) DEFAULT 'Open',
    created_at DATETIME DEFAULT GETDATE()
);
