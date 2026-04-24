# =============================================================================
# pages/schema_page.py - Schema Management Page
# =============================================================================
# This file renders the schema management page using Streamlit components:
#   - A file uploader (st.file_uploader) to upload the schema_metadata.json
#     file for ingestion into Pinecone.
#   - An "Ingest Schema" button to trigger the ingestion process via the API.
#   - A table displaying all currently indexed tables in Pinecone, with
#     their column details and metadata.
#   - Delete buttons next to each table to remove its embeddings from Pinecone.
#   - A "Refresh" button to reload the list of indexed tables.
#   - Status messages for successful ingestion, deletion, or errors.
# Calls api_client.ingest_schema() and api_client.get_indexed_tables().
# =============================================================================
