-- Revert 003: Drop property-management operational tables

IF EXISTS (SELECT * FROM sys.tables WHERE name = 'charges')
DROP TABLE charges;

IF EXISTS (SELECT * FROM sys.tables WHERE name = 'work_orders')
DROP TABLE work_orders;

IF EXISTS (SELECT * FROM sys.tables WHERE name = 'leases')
DROP TABLE leases;

IF EXISTS (SELECT * FROM sys.tables WHERE name = 'residents')
DROP TABLE residents;

IF EXISTS (SELECT * FROM sys.tables WHERE name = 'units')
DROP TABLE units;
