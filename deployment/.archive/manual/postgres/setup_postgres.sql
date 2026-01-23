-- PostgreSQL Database Setup for SciTeX Cloud
-- Run as postgres user: sudo -u postgres psql -f tmp/setup_postgres.sql

-- Create development database and user
CREATE DATABASE scitex_cloud_dev;
CREATE USER scitex_dev WITH PASSWORD 'scitex_dev_2025';
GRANT ALL PRIVILEGES ON DATABASE scitex_cloud_dev TO scitex_dev;
ALTER DATABASE scitex_cloud_dev OWNER TO scitex_dev;

-- Create production database and user
CREATE DATABASE scitex_cloud_prod;
CREATE USER scitex_prod WITH PASSWORD 'CHANGE_THIS_IN_PRODUCTION';
GRANT ALL PRIVILEGES ON DATABASE scitex_cloud_prod TO scitex_prod;
ALTER DATABASE scitex_cloud_prod OWNER TO scitex_prod;

-- Enable extensions for both databases
\c scitex_cloud_dev
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- For similarity searches
CREATE EXTENSION IF NOT EXISTS unaccent;  -- For accent-insensitive search

\c scitex_cloud_prod
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- Grant schema permissions (PostgreSQL 15+)
\c scitex_cloud_dev
GRANT ALL ON SCHEMA public TO scitex_dev;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO scitex_dev;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO scitex_dev;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO scitex_dev;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO scitex_dev;

\c scitex_cloud_prod
GRANT ALL ON SCHEMA public TO scitex_prod;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO scitex_prod;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO scitex_prod;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO scitex_prod;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO scitex_prod;

-- Display created databases
\l scitex_cloud_*
