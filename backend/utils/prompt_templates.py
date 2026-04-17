# =============================================================================
# utils/prompt_templates.py - LLM Prompt Templates
# =============================================================================
# This file stores all prompt templates used when communicating with the
# Groq LLM. Keeping prompts separate from logic allows easy tuning:
#   - SYSTEM_PROMPT: Sets the LLM's role as a T-SQL expert that generates
#     valid SQL Server queries.
#   - SQL_GENERATION_PROMPT: Template that combines the user's NL query
#     with retrieved table schemas, instructing the LLM to produce a
#     correct SQL query.
#   - FEW_SHOT_EXAMPLES: (Optional) Example NL-to-SQL pairs to improve
#     the quality of generated queries via in-context learning.
# =============================================================================
