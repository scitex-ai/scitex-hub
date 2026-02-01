-- Create umami database if it doesn't exist
-- This script runs on PostgreSQL container startup

SELECT 'CREATE DATABASE umami'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'umami')\gexec
