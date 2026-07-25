import streamlit as st

st.set_page_config(page_title="PaperTrail — Integrations", page_icon="🔑")
st.title("🔑 Integrations")

st.markdown("""
PaperTrail uses **your own API keys** to run — nothing is stored on our servers.
Keys are kept only in this browser session and are cleared when you close or
refresh the tab. You'll need to re-enter them if you return later — this is a
deliberate privacy choice, not a limitation.
""")

st.divider()

st.subheader("LLM Provider — Groq")
st.caption(
    "This app uses `openai/gpt-oss-120b` via Groq. This model is fixed — it "
    "was tested extensively for reliable structured-output behavior across "
    "all of PaperTrail's workflows, so it isn't user-selectable."
)
groq_key = st.text_input(
    "Groq API Key", type="password",
    value=st.session_state.get("groq_api_key", ""),
    placeholder="gsk_...",
)
st.caption("Don't have one? [Get a free Groq API key](https://console.groq.com/keys)")
if groq_key:
    st.session_state["groq_api_key"] = groq_key

st.divider()

st.subheader("Document Processing — PageIndex")
st.caption("Used to parse and index your uploaded PDFs for Ask and Synthesize.")
pageindex_key = st.text_input(
    "PageIndex API Key", type="password",
    value=st.session_state.get("pageindex_api_key", ""),
    placeholder="Your PageIndex API key",
)
st.caption("Don't have one? [Get a PageIndex API key](https://pageindex.ai)")
if pageindex_key:
    st.session_state["pageindex_api_key"] = pageindex_key

st.divider()

st.subheader("Status")
col1, col2 = st.columns(2)
with col1:
    st.success("Groq key set") if st.session_state.get("groq_api_key") else st.warning("Groq key not set")
with col2:
    st.success("PageIndex key set") if st.session_state.get("pageindex_api_key") else st.warning("PageIndex key not set")

if st.session_state.get("groq_api_key") and st.session_state.get("pageindex_api_key"):
    st.info("You're all set! Head to **Ask**, **Discover**, or **Synthesize** from the sidebar.")
