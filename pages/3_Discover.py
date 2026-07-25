import requests
import streamlit as st
from shared.utils import require_keys, get_llm
from Discover.logic import discover_papers

st.set_page_config(page_title="PaperTrail — Discover", page_icon="🔍")
st.title("🔍 Discover")

if not require_keys(need_groq=True, need_pageindex=False):
    st.stop()

st.caption("Search arXiv. Results are filtered so only papers genuinely about your topic are shown. arXiv only.")

query = st.text_input("What are you looking for?", placeholder="e.g. transformer architectures for speech")
max_results = st.slider("Number of results", min_value=1, max_value=10, value=5)

if st.button("Search", type="primary") and query:
    with st.status("Searching arXiv...", expanded=True) as status:
        status.write("Interpreting your query...")
        llm = get_llm()
        try:
            response = discover_papers(llm, query, max_results=max_results)
            status.update(label="Search complete", state="complete")
        except Exception as e:
            status.update(label="Search failed", state="error")
            st.error(f"Something went wrong searching arXiv: {e}")
            response = None

    if response:
        st.session_state["discover_results"] = response

response = st.session_state.get("discover_results")

if response:
    if response["result_note"]:
        st.warning(response["result_note"])

    for paper in response["results"]:
        with st.container(border=True):
            st.markdown(f"### [{paper['title']}]({paper['link']})")
            st.caption(f"👤 {paper['authors']}  |  📅 {paper['published']}")

            with st.expander("Abstract & download"):
                st.write(paper.get("summary", "No abstract available."))

                state_key = f"pdf_bytes_{paper['arxiv_id']}"
                if state_key in st.session_state:
                    st.download_button(
                        "⬇ Download PDF",
                        data=st.session_state[state_key],
                        file_name=f"{paper['title'][:80]}.pdf",
                        mime="application/pdf",
                        key=f"dl_{paper['arxiv_id']}",
                    )
                else:
                    if st.button("Prepare download", key=f"prep_{paper['arxiv_id']}"):
                        try:
                            pdf_response = requests.get(paper["pdf_url"], timeout=30)
                            pdf_response.raise_for_status()
                            st.session_state[state_key] = pdf_response.content
                        except Exception as e:
                            st.error(f"Couldn't fetch this PDF: {e}")
