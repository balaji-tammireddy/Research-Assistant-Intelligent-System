import streamlit as st
from shared.utils import (
    keys_ready, render_key_status_badges, render_header,
    get_llm, ingest_pdfs, build_document_index, show_error_toast,
    render_section_header, status_badge,
)
from Ask.logic import answer_query, update_chat_history

from pathlib import Path

ICON = Path(__file__).resolve().parent.parent / "assets" / "favicon.png"

st.set_page_config(
    page_title="PaperTrail",
    page_icon=str(ICON),
    layout="wide",
)


render_header("ask", "Ask", "Chat with your documents — grounded answers with exact section citations.")
render_key_status_badges(need_groq=True, need_pageindex=True)

ready = keys_ready(need_groq=True, need_pageindex=True)

if "ask_document_trees" not in st.session_state:
    st.session_state["ask_document_trees"] = {}
    st.session_state["ask_document_index"] = []
    st.session_state["ask_chat_history"] = []

document_trees = st.session_state["ask_document_trees"]
has_docs = bool(document_trees)

with st.container(key="panels_row"):
    left, right = st.columns([3, 7], border=True)

    # ---------------- Left: documents ----------------
    with left:
        with st.container(key="ask_doc_area", height="stretch"):
            render_section_header("document", "Documents")

            doc_list_slot = st.container(key="ask_doc_list", height="stretch")
            with doc_list_slot:
                if has_docs:
                    st.caption(f"{len(document_trees)} document(s) loaded")
                    for d in document_trees.values():
                        st.markdown(
                            f'<div class="pt-file-row">{status_badge("ok")}'
                            f'<span class="pt-file-name">{d["filename"]}</span></div>',
                            unsafe_allow_html=True,
                        )
                elif ready:
                    st.markdown(
                        '<div class="pt-empty-fill"><div class="pt-caution-box">'
                        'Upload at least one PDF below, then click <b>Process documents</b>.'
                        '</div></div>',
                        unsafe_allow_html=True,
                    )

            # Uploader + process button pinned at the bottom of the panel.
            uploaded_files = st.file_uploader(
                "Upload PDFs", type=["pdf"], accept_multiple_files=True,
                key="ask_uploader", label_visibility="collapsed",
                disabled=not ready,
            )
            process_clicked = st.button(
                "Process documents", width="stretch", type="primary",
                disabled=not ready or not uploaded_files,
            )

            if process_clicked:
                with doc_list_slot:
                    placeholders = {f.name: st.empty() for f in uploaded_files}
                    document_trees = ingest_pdfs(uploaded_files, placeholders=placeholders)
                st.session_state["ask_document_trees"] = document_trees
                st.session_state["ask_document_index"] = build_document_index(document_trees)
                st.session_state["ask_chat_history"] = []
                st.rerun()

    # ---------------- Right: chat ----------------
    with right:
        with st.container(key="ask_chat_area", height="stretch"):
            render_section_header("chat", "Chat")

            chat_slot = st.container(key="ask_chat_messages", height="stretch")
            with chat_slot:
                if not has_docs:
                    st.markdown(
                        '<div class="pt-empty-fill"><div class="pt-caution-box">'
                        '⚠ Add at least one file on the left to start chatting.</div></div>',
                        unsafe_allow_html=True,
                    )
                else:
                    for msg in st.session_state["ask_chat_history"]:
                        if msg["role"] in ("user", "assistant"):
                            with st.chat_message(msg["role"]):
                                st.write(msg["content"])
                                by_paper = msg.get("sources_by_paper")
                                if by_paper:
                                    with st.expander("Sources", expanded=False):
                                        for filename, entries in by_paper.items():
                                            nums = " ".join(f"`[{e['index']}]`" for e in entries)
                                            st.markdown(f"**{filename}** {nums}")
                                            for e in entries:
                                                st.caption(f"[{e['index']}] {e['section_short']}")

            # Placed inside the panel container so Streamlit pins it to the
            # bottom of *this* panel, not the bottom of the whole page.
            question = st.chat_input(
                "Ask a question about your uploaded papers...",
                disabled=not (ready and has_docs),
            )

            if question and has_docs:
                with chat_slot:
                    with st.chat_message("user"):
                        st.write(question)

                    with st.chat_message("assistant"):
                        with st.spinner("Searching your documents..."):
                            try:
                                llm = get_llm()
                                result = answer_query(
                                    llm, question,
                                    document_trees,
                                    st.session_state["ask_document_index"],
                                    st.session_state["ask_chat_history"],
                                )
                                st.write(result["answer"])
                                if result.get("sources_by_paper"):
                                    with st.expander("Sources", expanded=False):
                                        for filename, entries in result["sources_by_paper"].items():
                                            nums = " ".join(f"`[{e['index']}]`" for e in entries)
                                            st.markdown(f"**{filename}** {nums}")
                                            for e in entries:
                                                st.caption(f"[{e['index']}] {e['section_short']}")
                            except Exception as e:
                                show_error_toast(f"Something went wrong answering that question: {e}")
                                result = None

                if result:
                    st.session_state["ask_chat_history"] = update_chat_history(
                        get_llm(), st.session_state["ask_chat_history"], question, result["answer"]
                    )
                    st.session_state["ask_chat_history"][-1]["sources_by_paper"] = result.get("sources_by_paper", {})
                    st.rerun()