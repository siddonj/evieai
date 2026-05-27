-- 001: Initial schema — contacts and companies tables
-- Applies:   mcp_servers/sql/migrations/001_initial_schema.up.sql
-- Reverts:   mcp_servers/sql/migrations/001_initial_schema.down.sql

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'contacts')
CREATE TABLE contacts (
    id INT IDENTITY(1,1) PRIMARY KEY,
    first_name NVARCHAR(50) NOT NULL,
    last_name NVARCHAR(50) NOT NULL,
    email NVARCHAR(100),
    phone NVARCHAR(30),
    company NVARCHAR(100),
    job_title NVARCHAR(100),
    stage NVARCHAR(50),
    deal_value DECIMAL(12,2),
    region NVARCHAR(50),
    owner NVARCHAR(100),
    last_contact_date DATE,
    notes NVARCHAR(500)
);

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'companies')
CREATE TABLE companies (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(100) NOT NULL,
    industry NVARCHAR(100),
    revenue_tier NVARCHAR(50),
    employee_count INT,
    region NVARCHAR(50),
    website NVARCHAR(200),
    annual_revenue BIGINT,
    active_deals INT
);
