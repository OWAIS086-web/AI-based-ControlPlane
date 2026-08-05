-- Runs once on first postgres volume init.
-- Creates the maintenance DB alongside the main controlplane DB.
SELECT 'CREATE DATABASE maintenance_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'maintenance_db')\gexec
