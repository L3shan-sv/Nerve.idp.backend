-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable full text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Audit log is append-only — revoke UPDATE/DELETE from app user
-- (run after tables are created by alembic)
-- REVOKE UPDATE, DELETE ON audit_log FROM nerve;
