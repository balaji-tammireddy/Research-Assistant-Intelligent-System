import streamlit as st
from shared.utils import inject_global_css, ICONS
from pathlib import Path


ICON = Path(__file__).resolve().parent / "assets" / "favicon.png"

st.set_page_config(
    page_title="PaperTrail",
    page_icon=str(ICON),
    layout="wide",
)

inject_global_css()

# --- Top bar: title on the left, Get Started on the top-right (H2) ---
top_left, top_right = st.columns([4, 1])
with top_left:
    st.markdown(
        f'<div class="pt-panel-header">{ICONS["home"]}'
        f'<span class="pt-title" style="font-size:2rem;">PaperTrail</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="pt-tagline" style="font-size:1.05rem;">'
        'A citation-grounded research assistant for working with papers.</div>',
        unsafe_allow_html=True,
    )
with top_right:
    st.write("")
    if st.button("Get started →", type="primary", use_container_width=True):
        st.switch_page("pages/1_Integrations.py")

st.caption(
    "Bring your own AI provider keys — nothing runs on a shared backend, and no "
    "documents or keys are stored beyond your current browser session."
)

st.divider()

# --- Three modules, each with a short tagline (H3 + H4) ---
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f'<div class="pt-panel-header">{ICONS["ask"]}<span class="pt-title" style="font-size:1.2rem;">Ask</span></div>', unsafe_allow_html=True)
    st.markdown('*Chat with your documents.*')
    st.write("Upload PDFs and get grounded answers with exact section citations — no hallucinated claims.")

with col2:
    st.markdown(f'<div class="pt-panel-header">{ICONS["discover"]}<span class="pt-title" style="font-size:1.2rem;">Discover</span></div>', unsafe_allow_html=True)
    st.markdown('*Find the papers worth reading.*')
    st.write("Search arXiv with LLM-filtered relevance, so results are actually about your topic.")

with col3:
    st.markdown(f'<div class="pt-panel-header">{ICONS["synthesize"]}<span class="pt-title" style="font-size:1.2rem;">Synthesize</span></div>', unsafe_allow_html=True)
    st.markdown('*Turn a stack of papers into one review.*')
    st.write("Generate a structured literature review — themes, methodology, findings, gaps. Downloadable as PDF.")

st.divider()

# --- How it works: attractive, scannable, not skippable (H5) ---
st.markdown("### How it works")

hcol1, hcol2, hcol3 = st.columns(3)
with hcol1:
    st.markdown("#### 🔑 Bring your own keys")
    st.write(
        "A [Groq](https://console.groq.com/keys) key powers the LLM, and a "
        "[PageIndex](https://pageindex.ai) key parses your documents. Both live "
        "only in this browser session — never written to a server or database."
    )
with hcol2:
    st.markdown("#### 🎯 One fixed, tested model")
    st.write(
        "The LLM is locked to `openai/gpt-oss-120b` on Groq — chosen after "
        "testing showed it gave the most reliable structured output across "
        "all three tools, so there's nothing to misconfigure."
    )
with hcol3:
    st.markdown("#### 🌳 Vectorless retrieval")
    st.write(
        "Papers are parsed into a structured section tree instead of embedding "
        "chunks. The assistant reads section titles and summaries to decide "
        "what's relevant, so citations point to real section names — not "
        "arbitrary chunk numbers."
    )

st.divider()

# --- README-style project details, for anyone evaluating the project (H7) ---
with st.expander("📋 About this project — architecture, design decisions & tech stack", expanded=False):
    st.markdown("""
**PaperTrail** is a citation-grounded research assistant built around three
tools — Ask, Discover, and Synthesize — sharing a common document-ingestion
and BYOK (bring-your-own-key) layer.

**Why vectorless retrieval?**
Most RAG systems chunk documents into fixed-size pieces and embed them, which
throws away document structure and produces citations that point to
meaningless chunk IDs. PaperTrail instead parses each PDF into a structured
section tree (via PageIndex), then uses an LLM tree-search step to pick the
relevant node IDs directly from titles + summaries before pulling in full
text — so citations always resolve to a real, human-readable section name.

**Ask** — Retrieval-augmented Q&A over uploaded papers. An LLM searches the
document tree(s) for relevant sections, pulls their full text, and answers
strictly from that context with inline citations. Supports cross-paper
comparison questions and keeps a sliding-window chat history (older turns are
summarized rather than dropped).

**Discover** — arXiv search with a disambiguation step (e.g. "transformers"
→ ML architecture vs. hardware), category filtering, and a strict LLM
relevance filter that rejects papers merely *mentioning* a topic rather than
being about it. Includes one bounded retry with reworded search terms if the
first pass comes up short.

**Synthesize** — An orchestrator-worker pipeline (via LangGraph) that builds
shared context across all uploaded papers (themes + per-paper facts), then
writes an Overview, Thematic Grouping, Methodology Comparison table, Key
Findings Comparison (explicitly calling out agreement/disagreement between
papers), and Gaps & Future Directions — assembled into one review,
exportable as PDF.

**Tech stack:** Streamlit (UI), LangChain + LangGraph (orchestration), Groq
(`openai/gpt-oss-120b` LLM), PageIndex (structured PDF parsing), `arxiv`
(paper search), ReportLab (PDF export).

**Design principles:** no server-side storage of keys or documents, one
fixed model to keep behavior predictable, and citations that trace back to
real sections rather than opaque chunk indices.
""")
