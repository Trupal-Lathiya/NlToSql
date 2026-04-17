# =============================================================================
# utils/helpers.py - General Utility / Helper Functions
# =============================================================================
# This file contains shared helper functions used across the application:
#   - SQL sanitization: Basic validation to prevent dangerous SQL operations
#     (e.g., DROP, DELETE, ALTER) from being executed.
#   - Response formatting: Convert raw database rows into structured
#     dictionaries or JSON-friendly formats.
#   - Schema text builder: Convert table metadata (name, columns, types)
#     into a human-readable text description for the LLM prompt.
#   - Logging helpers: Standardized logging for debugging the pipeline.
# =============================================================================
