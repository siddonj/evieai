-- Revert 001: Drop contacts and companies tables

IF EXISTS (SELECT * FROM sys.tables WHERE name = 'contacts')
DROP TABLE contacts;

IF EXISTS (SELECT * FROM sys.tables WHERE name = 'companies')
DROP TABLE companies;
