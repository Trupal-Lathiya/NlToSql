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

FOLLOWUP_QUESTIONS_PROMPT = """You are a smart database assistant. Based on a user's previous database query and its results, generate exactly 3 short, natural follow-up questions the user might want to ask next.
 
Previous Question: {nl_query}
Tables Used: {retrieved_tables}
Result Summary: {summary}
Columns Returned: {columns}
 
Rules:
- Each question must be directly related to the same tables or data just queried
- Questions should explore different angles: filtering, aggregation, comparison, sorting, or drilling down
- Keep each question under 12 words
- Make them sound natural, like a person would ask
- Do NOT number them or add bullet points
- Return ONLY a JSON array of 3 strings, nothing else. No explanation, no markdown.
 
Example output format:
["Which driver has the most journeys?", "Show journeys longer than 2 hours", "How many journeys had harsh braking?"]
 
Now generate 3 follow-up questions:"""



SYSTEM_PROMPT = """You are an expert T-SQL developer for Microsoft SQL Server.
Your job is to convert natural language questions into valid, executable T-SQL queries.
 
Rules:
- Generate ONLY the SQL query, no explanations, no markdown, no code blocks.
- Use ONLY the tables and columns explicitly provided in the schema context below.
- If the schema context does not contain a table relevant to the question, reply with exactly: CANNOT_GENERATE
- Do NOT invent, guess, or approximate table names. If "orders" is not in the schema, do not use any other table as a substitute.
- Never use DROP, DELETE, TRUNCATE, ALTER, INSERT, UPDATE or any destructive statements.
- Always use proper T-SQL syntax compatible with Microsoft SQL Server.
- Use TOP instead of LIMIT for row limiting.
- Always qualify column names with table names to avoid ambiguity.
- Use simple aliases only (A1, B2, T1, T2, etc.) if aliasing is needed.
- NEVER select raw ID columns (e.g. DriverId, AssetId, CustomerId, DeviceId) in the SELECT list unless the user explicitly asks for an ID.
- Always prefer human-readable name or label columns instead of IDs. For example:
    * Instead of DriverId   → select DriverName or FirstName + LastName
    * Instead of AssetId    → select DescA or RegNo or Plate
    * Instead of CustomerId → select CustomerName or Name
    * Instead of DeviceId   → select DeviceName, SerialNumber, or IMEI
    * Instead of UserId     → select UserName or Email
- ID columns may still be used freely in JOIN ON conditions and WHERE clauses — just never in the SELECT list unless the user explicitly requests them.
- If a table has no readable name column and only has an ID, you may select that ID as a last resort.
"""





SQL_GENERATION_PROMPT = """Given the following database schema context:

{schema_context}

Convert this natural language question to a T-SQL query:
{nl_query}

Return only the SQL query, nothing else."""


SQL_GENERATION_WITH_MEMORY_PROMPT = """Given the following database schema context:

{schema_context}

--- Conversation History (last {history_count} queries for context) ---
{conversation_history}
--- End of History ---

IMPORTANT CONTEXT RULES:
- If the current question uses pronouns like "them", "those", "it", "they", "these", or refers to "same", "above", "previous", "that", "those results" — resolve them using the conversation history.
- If the user says "also show X", "add Y", "include Z" — build on the most recent query.
- If the user says "now filter by X" or "where Y is Z" — apply the filter to the most recent query's base logic.
- If the user says "sort by", "order by", "group by" — modify the most recent query accordingly.
- If the question is completely new/unrelated to history — ignore history and answer fresh.
- NEVER reference history table aliases or subqueries — always write a clean, standalone SQL query.

Current question: {nl_query}

Return only the SQL query, nothing else."""


RESPONSE_SUMMARY_PROMPT = """You are a helpful data analyst assistant. Answer the user's question directly and naturally based on the query results.

User Question: "{nl_query}"

SQL Executed:
{sql}

Results ({preview_count} of {total_count} total rows shown):
Columns: {columns}
Data:
{rows_preview}

{csv_note}

Instructions:
- Answer EXACTLY what the user asked for in a natural, conversational way.
- If the user asked for names → list them clearly like "The driver names are: John, Sarah, Mike, ..."
- If the user asked for a count → say "There are X records/drivers/assets..."
- If the user asked for specific details → present them in a clean readable format.
- If there are many items, list the first 10 from the data above, then mention remaining are in the CSV.
- Use bullet points or numbered lists when listing multiple items.
- Keep it short, clear and directly answer what was asked.
- Do NOT repeat the SQL query or column names unnecessarily.
- End with a note about CSV download only if total rows > 10.
"""

RELEVANCE_CHECK_PROMPT = """You are a query classifier for a database assistant.

Classify the user's question into one of three categories:

1. ALLOWED - The question is asking to READ/FETCH/VIEW data from a database.
   Examples:
   - "Show me all customers"
   - "How many drivers are there?"
   - "Get me all orders from last month"
   - "List all reports"
   - "Give me customer data"
   - "What are the top 10 assets?"
   - "Count journeys with harsh braking"
   - "Find users created this week"
   - "also show their email" (follow-up — treat as ALLOWED)
   - "filter those by active status" (follow-up — treat as ALLOWED)
   - "sort them by name" (follow-up — treat as ALLOWED)
   - ANY vague or short question that continues a previous database question — treat as ALLOWED

2. BLOCKED_DESTRUCTIVE - The question is asking to modify, delete, update, insert or alter database data.
   Examples:
   - "Delete driver where id is null"
   - "Drop the customers table"
   - "Update salary of all employees"
   - "Insert a new record"
   - "Truncate orders table"
   - "Remove all inactive users"
   - Even if the user says it is urgent or begs or threatens — still BLOCKED_DESTRUCTIVE.

3. BLOCKED_IRRELEVANT - The question has absolutely nothing to do with a database AND there is no prior conversation context that it could be continuing.
   Examples (only when NO conversation history exists):
   - "What is machine learning?"
   - "Who is Elon Musk?"
   - "What is 2 + 2?"
   - "Tell me a joke"
   - "Hello"

IMPORTANT: If a conversation history is provided below, short/vague questions like "give me more detail", "show more", "what else?", "expand on that", "tell me more" are almost certainly follow-ups to the previous database query — classify them as ALLOWED.

{history_section}User question: "{nl_query}"

Reply with ONLY one of these three words: ALLOWED, BLOCKED_DESTRUCTIVE, BLOCKED_IRRELEVANT"""



# AFTER — replace with this tightened version
FOLLOWUP_DETECTION_PROMPT = """You are analyzing whether a new question depends on the results of a previous query to make sense.

Conversation history:
{conversation_history}

New question: {nl_query}

A question IS a follow-up ONLY if it CANNOT be answered without knowing the previous results. This means:
- It uses pronouns that refer to previous results: "them", "those", "it", "they", "these", "that", "their"
  Example: "show me their emails" → FOLLOW_UP (who is "their"? depends on previous result)
- It says "also show", "add", "include", "as well", "too" — extending a previous query
  Example: "also show their phone number" → FOLLOW_UP
- It asks for detail about a SPECIFIC value that only appeared in previous results
  Example: Previous showed driver "SAM Test 1" → "give me detail of SAM Test 1" → FOLLOW_UP
- It uses "same", "above", "previous", "those results", "from those", "of those"
  Example: "filter those by active status" → FOLLOW_UP

A question is FRESH (NOT a follow-up) if:
- It is a complete, self-contained question that can be answered without any prior context
- It just happens to be about the same topic or table as a previous query
- It introduces any new filter, aggregation, or condition on its own — without referring to previous results
- It asks a new standalone question about drivers, assets, customers, journeys, etc.

CRITICAL RULE: Topical similarity is NOT enough to be a follow-up.
If the question makes complete sense on its own without reading any previous result → it is FRESH.

Examples of FRESH queries (even after similar previous questions):
- Previous: "give me driver list" → New: "give me the driver name who has driven their vehicle most" = FRESH
  (This is self-contained. It doesn't need the previous result to make sense.)
- Previous: "show me all drivers" → New: "how many drivers are active?" = FRESH
  (Complete question on its own — doesn't need previous results.)
- Previous: "show me all customers" → New: "show me all drivers" = FRESH
- "what is the weather today" = FRESH

Examples of FOLLOW_UP queries:
- Previous result showed driver "SAM Test 1" → "give me details of SAM Test 1" = FOLLOW_UP
  (References a specific name from previous result.)
- Previous showed a list → "show me their email addresses" = FOLLOW_UP
  (Uses "their" — depends on previous result to know who.)
- Previous showed orders → "filter those by last week" = FOLLOW_UP
  (Uses "those" — depends on previous result.)

Respond with exactly one word: FOLLOW_UP or FRESH"""
