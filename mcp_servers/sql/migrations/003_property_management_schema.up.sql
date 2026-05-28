-- 003: Property-management schema inspired by Entrata/Yardi workflows (synthetic)
-- Adds operational tables for leases, residents, units, work orders, and charges.

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
);

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
);

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
);

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
);

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
);
