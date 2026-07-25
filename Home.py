import streamlit as st

st.set_page_config(page_title="PaperTrail", page_icon="📄", layout="wide")

st.title("📄 PaperTrail")
st.subheader("A citation-grounded research assistant for working with papers")

st.markdown("""
PaperTrail helps you read, search, and synthesize research papers using your
own AI provider keys — nothing runs on a shared backend, and no documents or
keys are stored beyond your current browser session.

It has three tools, available from the sidebar:
""")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 💬 Ask")
    st.write(
        "Upload one or more PDFs and ask questions about them. Answers are "
        "grounded strictly in your uploaded papers and cite the exact "
        "section they came from — no hallucinated claims. Supports "
        "questions that compare across multiple papers at once."
    )

with col2:
    st.markdown("### 🔍 Discover")
    st.write(
        "Search arXiv for papers on any topic. Results are filtered by an "
        "LLM step that checks each paper is genuinely *about* your topic, "
        "not just superficially mentioning it — and retries with a "
        "reworded search if the first pass comes up short."
    )

with col3:
    st.markdown("### 📝 Synthesize")
    st.write(
        "Upload several papers and generate a structured literature review "
        "— overview, thematic grouping, a methodology comparison table, a "
        "findings comparison that calls out agreements and disagreements "
        "between papers, and open gaps. Downloadable as PDF."
    )

st.divider()

st.markdown("""
### How it works
- **Bring your own keys.** PaperTrail uses a [Groq](https://console.groq.com/keys)
  key for the LLM and a [PageIndex](https://pageindex.ai) key for document
  parsing. Both are entered on the Integrations page and kept only in this
  session — never written to a server or database.
- **Fixed model.** The LLM is fixed to `openai/gpt-oss-120b` on Groq, chosen
  after testing showed it gave the most reliable structured output across
  all three tools.
- **Vectorless retrieval.** Instead of chunking documents into embeddings,
  papers are parsed into a structured section tree (via PageIndex). The
  assistant reads section titles and summaries to decide what's relevant,
  then pulls in only the full text it actually needs — which is also what
  makes citations point to real section names instead of arbitrary chunks.
""")

st.divider()
if st.button("Get started — set up your keys →", type="primary"):
    st.switch_page("pages/1_Integrations.py")
