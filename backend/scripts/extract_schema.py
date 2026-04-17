# =============================================================================
# scripts/extract_schema.py - Auto-Extract Schema from SQL Server
# =============================================================================
# This is a standalone script that connects to your SQL Server database
# and automatically extracts the schema metadata (table names, column
# names, data types, primary/foreign keys, constraints) by querying
# INFORMATION_SCHEMA views and sys tables.
# It outputs the extracted schema to data/schema_metadata.json in the
# format expected by the ingestion script.
# Usage: python scripts/extract_schema.py
# =============================================================================
