import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(
    page_title="NL2SQL Chat",
    page_icon="🗄️",
    layout="wide"
)

st.markdown("""
<style>
#MainMenu, footer, header { visibility: hidden; }

.main .block-container {
    padding-bottom: 120px !important;
    padding-top: 1rem !important;
    max-width: 860px !important;
    margin: 0 auto !important;
}

.user-bubble {
    background: #2563eb;
    color: white;
    padding: 12px 18px;
    border-radius: 18px 18px 4px 18px;
    margin: 6px 0;
    max-width: 75%;
    margin-left: auto;
    font-size: 0.95rem;
    line-height: 1.5;
    word-wrap: break-word;
}

.assistant-bubble {
    background: #1e1e2e;
    color: #e2e8f0;
    padding: 14px 18px;
    border-radius: 18px 18px 18px 4px;
    margin: 6px 0;
    max-width: 85%;
    font-size: 0.95rem;
    line-height: 1.5;
    border: 1px solid #2a2a3d;
    word-wrap: break-word;
}

.avatar-user {
    text-align: right;
    font-size: 0.72rem;
    color: #94a3b8;
    margin-bottom: 2px;
    padding-right: 4px;
}
.avatar-assistant {
    text-align: left;
    font-size: 0.72rem;
    color: #94a3b8;
    margin-bottom: 2px;
    padding-left: 4px;
}
.msg-time {
    font-size: 0.68rem;
    color: #475569;
    margin-top: 4px;
}
.welcome-box {
    text-align: center;
    padding: 80px 20px;
    color: #475569;
}
.welcome-box h2 {
    color: #e2e8f0;
    font-size: 1.8rem;
    margin-bottom: 10px;
}
.memory-badge {
    display: inline-block;
    background: #1e3a5f;
    color: #7dd3fc;
    border: 1px solid #1d4ed8;
    font-size: 0.68rem;
    padding: 2px 8px;
    border-radius: 12px;
    margin-left: 6px;
    vertical-align: middle;
}

@keyframes fadeSlideIn {
    from { opacity: 0; transform: translateY(10px); }
    to   { opacity: 1; transform: translateY(0); }
}
.user-bubble, .assistant-bubble {
    animation: fadeSlideIn 0.2s ease-out;
}
</style>
""", unsafe_allow_html=True)

# ── Session state init ─────────────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []
if "pending_query" not in st.session_state:
    st.session_state.pending_query = None
if "input_key" not in st.session_state:
    st.session_state.input_key = 0

from api_client import send_query
import pandas as pd

MEMORY_SIZE = 5

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🗄️ NL2SQL")
    st.markdown("Natural Language → SQL")
    st.divider()

    total = len(st.session_state.history)
    successful = [h for h in st.session_state.history if h.get("status") == "success"]
    memory_turns = min(len(successful), MEMORY_SIZE)

    st.caption(f"💬 {total} message(s) in session")

    # Memory indicator
    if memory_turns > 0:
        st.markdown(
            f"🧠 **Conversation Memory**  \n"
            f"Using last **{memory_turns}** successful quer{'y' if memory_turns == 1 else 'ies'} as context."
        )
        with st.expander("View remembered queries", expanded=False):
            for i, turn in enumerate(successful[-MEMORY_SIZE:], 1):
                q = turn.get("nl_query", "")
                st.markdown(f"`{i}.` {q[:60]}{'...' if len(q) > 60 else ''}")
    else:
        st.caption("🧠 Memory: no context yet")

    st.divider()
    if st.session_state.history:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.history = []
            st.session_state.pending_query = None
            st.rerun()
    st.divider()
    st.caption("Powered by Pinecone + Groq + SQL Server")

# ── Process pending query FIRST (before rendering) ────────────────────────
if st.session_state.pending_query:
    query = st.session_state.pending_query
    st.session_state.pending_query = None  # Clear immediately to stop loop

    with st.spinner("Thinking..."):
        from datetime import datetime

        # Pass current history as conversation context (only successful turns)
        result = send_query(
            nl_query=query,
            conversation_history=st.session_state.history,
        )
        result["nl_query"] = query
        result["timestamp"] = datetime.now().strftime("%H:%M:%S")

    st.session_state.history.append(result)
    st.rerun()

# ── Chat render ────────────────────────────────────────────────────────────
if not st.session_state.history:
    st.markdown("""
    <div class="welcome-box">
        <h2>🗄️ NL2SQL Chat</h2>
        <p>Ask any question about your database in plain English.<br/>
        I'll generate SQL and return the results instantly.</p>
        <br/>
        <p style="color:#334155;">Try: <em>"Show me all customers from Mumbai"</em></p>
        <p style="color:#334155;font-size:0.85rem;">Then follow up: <em>"now filter those by active status"</em> 🧠</p>
    </div>
    """, unsafe_allow_html=True)
else:
    successful_so_far = 0
    for idx, entry in enumerate(st.session_state.history):
        # Track how many successful turns happened BEFORE this entry
        context_count = min(successful_so_far, MEMORY_SIZE)
        if entry.get("status") == "success":
            successful_so_far += 1

        # ── User bubble ──
        memory_badge = (
            f'<span class="memory-badge">🧠 {context_count} turns in context</span>'
            if context_count > 0 else ""
        )
        st.markdown(
            f'<div class="avatar-user">You &nbsp;👤{memory_badge}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(f'<div class="user-bubble">{entry["nl_query"]}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="avatar-user msg-time">{entry.get("timestamp","")}</div>',
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        if entry.get("status") == "error":
            st.markdown('<div class="avatar-assistant">🗄️ NL2SQL</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="assistant-bubble">❌ {entry["message"]}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown('<div class="avatar-assistant">🗄️ NL2SQL</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="assistant-bubble">{entry.get("summary", "Query executed successfully.")}</div>',
                unsafe_allow_html=True,
            )

            with st.expander("🧾 View Generated SQL", expanded=False):
                st.code(entry["sql"], language="sql")
                with st.expander("📋 Tables used from Pinecone", expanded=False):
                    for t in entry.get("retrieved_tables", []):
                        st.markdown(f"- `{t}`")

            if entry.get("columns") and entry.get("rows") is not None:
                rows = entry["rows"]
                cols = entry["columns"]
                total = entry.get("total_row_count", len(rows))

                if rows:
                    df = pd.DataFrame(rows, columns=cols)
                    st.markdown(
                        f"<div style='font-size:0.8rem;color:#64748b;margin:4px 0 6px 0;'>"
                        f"Showing {len(rows)} of {total} rows</div>",
                        unsafe_allow_html=True,
                    )
                    st.dataframe(df, use_container_width=True)
                    csv_data = df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="⬇️ Download CSV",
                        data=csv_data,
                        file_name="results.csv",
                        mime="text/csv",
                        key=f"csv_{entry.get('timestamp','')}_{entry.get('nl_query','')[:10]}",
                    )
                else:
                    st.info("Query returned no results.")

        st.markdown(
            "<hr style='border:none;border-top:1px solid #1e293b;margin:16px 0;'/>",
            unsafe_allow_html=True,
        )

# ── Auto-scroll anchor ─────────────────────────────────────────────────────
st.markdown('<div id="bottom-anchor"></div>', unsafe_allow_html=True)

# ── Spacer ─────────────────────────────────────────────────────────────────
st.markdown("<div style='height:100px'></div>", unsafe_allow_html=True)

# ── Fixed bottom input ─────────────────────────────────────────────────────
col1, col2 = st.columns([10, 1])
with col1:
    user_input = st.text_input(
        label="chat_input",
        placeholder="Ask your database anything... or follow up: 'also show their email'",
        label_visibility="collapsed",
        key=f"chat_input_{st.session_state.input_key}",
    )
with col2:
    send = st.button("➤", use_container_width=True, type="primary")

st.markdown("""
<style>
section.main > div:last-child {
    position: fixed;
    bottom: 0;
    left: 240px;
    right: 0;
    background: #0e1117;
    border-top: 1px solid #1e293b;
    padding: 12px 32px 20px 32px;
    z-index: 9999;
}
</style>
""", unsafe_allow_html=True)

# ── Handle send ───────────────────────────────────────────────────────────
if (send or user_input) and user_input.strip():
    st.session_state.pending_query = user_input.strip()
    st.session_state.input_key += 1
    st.rerun()