-- 004: Ruckus R1 operational schema (synthetic)
-- Adds R1 sites, devices, event history, and daily KPI history tables.

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
);

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
);

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
);

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
);

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_r1_devices_site_id' AND object_id = OBJECT_ID('r1_devices')
)
CREATE INDEX IX_r1_devices_site_id ON r1_devices(site_id);

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_r1_device_events_device_ts' AND object_id = OBJECT_ID('r1_device_events')
)
CREATE INDEX IX_r1_device_events_device_ts ON r1_device_events(device_id, event_ts DESC);

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_r1_daily_metrics_device_date' AND object_id = OBJECT_ID('r1_device_daily_metrics')
)
CREATE INDEX IX_r1_daily_metrics_device_date ON r1_device_daily_metrics(device_id, metric_date DESC);
