-- Revert 004: Drop Ruckus R1 schema tables

IF EXISTS (SELECT * FROM sys.tables WHERE name = 'r1_device_daily_metrics')
DROP TABLE r1_device_daily_metrics;

IF EXISTS (SELECT * FROM sys.tables WHERE name = 'r1_device_events')
DROP TABLE r1_device_events;

IF EXISTS (SELECT * FROM sys.tables WHERE name = 'r1_devices')
DROP TABLE r1_devices;

IF EXISTS (SELECT * FROM sys.tables WHERE name = 'r1_sites')
DROP TABLE r1_sites;
