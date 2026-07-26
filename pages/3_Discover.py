import requests
import streamlit as st
from shared.utils import (
    keys_ready, render_key_status_badges, get_llm, show_error_toast,
    show_caution_toast, render_header,
)
from Discover.logic import discover_papers

from pathlib import Path

ICON = Path(__file__).resolve().parent.parent / "assets" / "favicon.png"

st.set_page_config(
    page_title="PaperTrail",
    page_icon=str(ICON),
    layout="wide",
)


render_header("discover", "Discover", "Find the papers worth reading — arXiv, filtered for genuine relevance.")
render_key_status_badges(need_groq=True, need_pageindex=False)

ready = keys_ready(need_groq=True, need_pageindex=False)

# ---- Inline row: search box + result-count stepper + search button (D1, D2) ----
c_query, c_count, c_btn = st.columns([6, 2, 2])
with c_query:
    query = st.text_input(
        "What are you looking for?", placeholder="e.g. transformer architectures for speech",
        label_visibility="collapsed", disabled=not ready,
    )
with c_count:
    max_results = st.number_input(
        "Results", min_value=1, max_value=10, value=5, step=1,
        label_visibility="collapsed", disabled=not ready,
    )
with c_btn:
    search_clicked = st.button("Search", type="primary", width="stretch", disabled=not ready)

if search_clicked and query:
    # Clear any per-card state (prepared downloads, expander-open flags) from
    # the previous search so old cards don't visually bleed into new results.
    for k in list(st.session_state.keys()):
        if k.startswith("pdf_bytes_") or k.startswith("expander_open_"):
            del st.session_state[k]

    with st.status("Searching arXiv...", expanded=True) as status:
        status.write("Interpreting your query...")
        llm = get_llm()
        try:
            response = discover_papers(llm, query, max_results=int(max_results))
            status.update(label="Search complete", state="complete")
        except Exception as e:
            status.update(label="Search failed", state="error")
            show_error_toast(f"Something went wrong searching arXiv: {e}")
            response = None

    if response:
        st.session_state["discover_results"] = response

response = st.session_state.get("discover_results")

if response:
    if response["result_note"]:
        show_caution_toast(response["result_note"])

    for i, paper in enumerate(response["results"]):
        with st.container(border=True, key=f"card_{i}_{paper['arxiv_id']}"):
            st.markdown(f"### [{paper['title']}]({paper['link']})")
            st.caption(f"👤 {paper['authors']}")
            st.caption(f"📅 {paper['published']}")

            expander_open_key = f"expander_open_{paper['arxiv_id']}"
            with st.expander("Abstract & download", expanded=st.session_state.get(expander_open_key, False),
                              key=f"exp_{i}_{paper['arxiv_id']}"):
                st.write(paper.get("summary", "No abstract available."))

                state_key = f"pdf_bytes_{paper['arxiv_id']}"
                if state_key in st.session_state:
                    st.download_button(
                        "⬇ Download PDF",
                        data=st.session_state[state_key],
                        file_name=f"{paper['title'][:80]}.pdf",
                        mime="application/pdf",
                        key=f"dl_{paper['arxiv_id']}",
                        type="primary",
                        use_container_width=True,
                    )
                else:
                    if st.button("Prepare download", key=f"prep_{paper['arxiv_id']}", type="primary", use_container_width=True):
                        # Bug fix (B5): the expander used to collapse back to closed on
                        # rerun after this click, hiding the download button that had
                        # actually appeared successfully. Pin it open via session_state
                        # so the download button is visible right after preparing.
                        st.session_state[expander_open_key] = True
                        try:
                            with st.spinner("Fetching PDF..."):
                                pdf_response = requests.get(paper["pdf_url"], timeout=30)
                                pdf_response.raise_for_status()
                                st.session_state[state_key] = pdf_response.content
                            st.rerun()
                        except Exception as e:
                            show_error_toast(f"Couldn't fetch this PDF: {e}")