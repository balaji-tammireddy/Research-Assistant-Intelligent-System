import streamlit as st
from shared.utils import render_header
from pathlib import Path

ICON = Path(__file__).resolve().parent.parent / "assets" / "favicon.png"

st.set_page_config(
    page_title="PaperTrail",
    page_icon=str(ICON),
    layout="wide",
)

render_header("key", "Integrations", "Bring your own keys — nothing is stored on our servers.")

st.markdown("""
PaperTrail uses **your own API keys** to run — nothing is stored on our servers.
Keys are kept only in this browser session and are cleared when you close or
refresh the tab. You'll need to re-enter them if you return later — this is a
deliberate privacy choice, not a limitation.
""")

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("Groq API Key")

    st.markdown("""
    <div style="min-height:70px;">
        <span style="color: rgba(250,250,250,0.6); font-size:0.95rem;">
        Powers the LLM (<code>openai/gpt-oss-120b</code>), fixed after testing
        showed it gave the most reliable structured output.
        </span>
    </div>
    """, unsafe_allow_html=True)

    groq_key = st.text_input(
        "Groq API Key",
        type="password",
        value=st.session_state.get("groq_api_key", ""),
        placeholder="gsk_...",
        label_visibility="collapsed",
    )

    st.caption("Don't have one? [Get a free Groq API key](https://console.groq.com/keys)")

    if groq_key:
        st.session_state["groq_api_key"] = groq_key

with col2:
    st.subheader("PageIndex API Key")

    st.markdown("""
    <div style="min-height:70px;">
        <span style="color: rgba(250,250,250,0.6); font-size:0.95rem;">
        Parses and indexes your uploaded PDFs into a structured section tree
        for Ask and Synthesize.
        </span>
    </div>
    """, unsafe_allow_html=True)

    pageindex_key = st.text_input(
        "PageIndex API Key",
        type="password",
        value=st.session_state.get("pageindex_api_key", ""),
        placeholder="Your PageIndex API key",
        label_visibility="collapsed",
    )

    st.caption("Don't have one? [Get a PageIndex API key](https://pageindex.ai)")

    if pageindex_key:
        st.session_state["pageindex_api_key"] = pageindex_key

if st.session_state.get("groq_api_key") and st.session_state.get("pageindex_api_key"):
    st.divider()
    st.info("You're all set! Head to **Ask**, **Discover**, or **Synthesize** from the sidebar.")
