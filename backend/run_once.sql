-- =============================================================================
-- run_once.sql
-- Run this ONCE in your SQL Server database to create the chat tables.
-- =============================================================================

-- Conversations table (one row per chat session)
CREATE TABLE NL2SQL_Conversations (
    Id            UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    UserId        NVARCHAR(450)    NOT NULL,        -- matches AspNetUsers.Id type
    Title         NVARCHAR(500)    NOT NULL DEFAULT 'New Chat',
    CreatedAt     DATETIME2        NOT NULL DEFAULT GETUTCDATE(),
    UpdatedAt     DATETIME2        NOT NULL DEFAULT GETUTCDATE()
);

CREATE INDEX IX_NL2SQL_Conversations_UserId ON NL2SQL_Conversations(UserId);

-- Messages table (one row per SUCCESSFUL query turn)
CREATE TABLE NL2SQL_Messages (
    Id              UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    ConversationId  UNIQUEIDENTIFIER NOT NULL
                        REFERENCES NL2SQL_Conversations(Id) ON DELETE CASCADE,
    NLQuery         NVARCHAR(MAX)    NOT NULL,
    GeneratedSQL    NVARCHAR(MAX)    NULL,
    Summary         NVARCHAR(MAX)    NULL,
    RetrievedTables NVARCHAR(MAX)    NULL,   -- stored as JSON string
    Columns         NVARCHAR(MAX)    NULL,   -- stored as JSON string
    Rows            NVARCHAR(MAX)    NULL,   -- stored as JSON string
    TotalRowCount   INT              NULL,
    CreatedAt       DATETIME2        NOT NULL DEFAULT GETUTCDATE()
);

CREATE INDEX IX_NL2SQL_Messages_ConversationId ON NL2SQL_Messages(ConversationId);