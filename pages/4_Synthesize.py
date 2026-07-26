import os
import tempfile
import streamlit as st
from shared.utils import (
    keys_ready, render_key_status_badges, render_header,
    get_llm, ingest_pdfs, show_error_toast, show_caution_toast, show_info_toast,
    render_section_header, status_badge, normalize_math_markdown, copy_to_clipboard_button,
)
from Synthesize.logic import generate_literature_review, export_review_to_pdf, get_copyable_text

from pathlib import Path

ICON = Path(__file__).resolve().parent.parent / "assets" / "favicon.png"

st.set_page_config(
    page_title="PaperTrail",
    page_icon=str(ICON),
    layout="wide",
)

render_header("synthesize", "Synthesize", "Turn a stack of papers into one structured literature review.")
render_key_status_badges(need_groq=True, need_pageindex=True)

ready = keys_ready(need_groq=True, need_pageindex=True)

if "synth_document_trees" not in st.session_state:
    st.session_state["synth_document_trees"] = {}

document_trees = st.session_state["synth_document_trees"]
has_docs = bool(document_trees)

with st.container(key="panels_row"):
    left, right = st.columns([3, 7], border=True)

    with left:
        render_section_header("document", "Documents")

        doc_list_slot = st.container(key="synth_doc_list", height=220)

        is_processing = st.session_state.get("synth_is_processing", False)

        with st.container(key="synth_upload_controls"):
            if not has_docs:
                uploaded_files = st.file_uploader(
                    "Upload PDFs",
                    type=["pdf"],
                    accept_multiple_files=True,
                    key="synth_uploader",
                    label_visibility="collapsed",
                    disabled=not ready or is_processing,
                )

                generate_clicked = st.button(
                    "Generating..." if is_processing else "Generate literature review",
                    width="stretch",
                    type="primary",
                    disabled=not ready or not uploaded_files or is_processing,
                )
            else:
                uploaded_files = None
                generate_clicked = False
                if st.button("Upload different documents", width="stretch"):
                    st.session_state["synth_document_trees"] = {}
                    st.session_state.pop("synth_review", None)
                    st.session_state.pop("synth_pdf_bytes", None)
                    st.rerun()

        # Phase 1: click sets the flag and reruns WITHOUT doing any work yet,
        # so the next run draws the button already-disabled before the
        # blocking ingest+generate calls start.
        if generate_clicked and not is_processing:
            st.session_state["synth_is_processing"] = True
            st.rerun()

        # Decide doc_list_slot's content only when not actively processing,
        # so a click's rerun shows ONLY the live ingestion progress.
        if not is_processing:
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
                        'Upload at least one PDF below, then click <b>Generate literature review</b>.'
                        '</div></div>',
                        unsafe_allow_html=True,
                    )

        # Phase 2: this run started with the flag already True.
        if is_processing and uploaded_files:
            with doc_list_slot:
                placeholders = {f.name: st.empty() for f in uploaded_files}
                document_trees = ingest_pdfs(uploaded_files, placeholders=placeholders)

            st.session_state["synth_document_trees"] = document_trees

            if not document_trees:
                show_error_toast("No documents processed successfully.")
                st.session_state["synth_is_processing"] = False
            else:
                if len(document_trees) == 1:
                    show_caution_toast(
                        "Only one document was uploaded — a literature review is usually "
                        "comparative, so this one may read more like a summary. Add another "
                        "paper for a fuller comparison."
                    )

                with st.spinner("Generating your literature review..."):
                    show_info_toast(
                        f"Generating review across {len(document_trees)} document(s) — "
                        f"this can take 30-60s across several synthesis steps."
                    )
                    try:
                        llm = get_llm()
                        result = generate_literature_review(llm, document_trees)
                        st.session_state["synth_review"] = result["review_text"]
                        st.session_state.pop("synth_pdf_bytes", None)
                    except Exception as e:
                        show_error_toast(f"Something went wrong generating the review: {e}")
                    finally:
                        st.session_state["synth_is_processing"] = False

            st.rerun()

    with right:
        with st.container(key="synth_result_area"):
            render_section_header("synthesize", "Review")
            review_text = st.session_state.get("synth_review")

            result_body = st.container(key="synth_result_body", height=520)

            with result_body:
                if not review_text:
                    st.markdown(
                        """
                        <div style="
                            height:260px;
                            display:flex;
                            align-items:center;
                            justify-content:center;
                        ">
                            <div class="pt-caution-box">
                                Add at least one PDF below, then click
                                <b>Generate literature review</b>.
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                else:
                    format_choice = st.selectbox("View as", ["Formatted", "Download PDF", "Copy as text"])

                    if format_choice == "Formatted":
                        st.markdown(normalize_math_markdown(review_text))

                    elif format_choice == "Download PDF":
                        if st.button("Prepare PDF"):
                            temp_path = os.path.join(tempfile.mkdtemp(), "literature_review.pdf")
                            export_review_to_pdf(review_text, temp_path)
                            with open(temp_path, "rb") as f:
                                st.session_state["synth_pdf_bytes"] = f.read()
                            os.remove(temp_path)

                        if "synth_pdf_bytes" in st.session_state:
                            st.download_button(
                                "⬇ Download literature_review.pdf",
                                data=st.session_state["synth_pdf_bytes"],
                                file_name="literature_review.pdf",
                                mime="application/pdf",
                                type="primary",
                            )

                    else:
                        copyable = get_copyable_text(review_text)
                        st.text_area("Copyable text", value=copyable, height=420, label_visibility="collapsed")
                        copy_to_clipboard_button(copyable)