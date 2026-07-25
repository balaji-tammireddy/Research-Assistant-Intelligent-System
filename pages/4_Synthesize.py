import html as _html
import os
import tempfile
import streamlit as st
from shared.utils import (
    keys_ready, render_key_status_badges, render_header,
    get_llm, ingest_pdfs, show_error_toast, show_caution_toast,
    render_section_header, status_badge,
)
from Synthesize.logic import generate_literature_review, export_review_to_pdf, get_copyable_text

st.set_page_config(page_title="PaperTrail — Synthesize", page_icon="📝", layout="wide")

render_header("synthesize", "Synthesize", "Turn a stack of papers into one structured literature review.")
render_key_status_badges(need_groq=True, need_pageindex=True)

ready = keys_ready(need_groq=True, need_pageindex=True)

if "synth_document_trees" not in st.session_state:
    st.session_state["synth_document_trees"] = {}

document_trees = st.session_state["synth_document_trees"]
has_docs = bool(document_trees)

with st.container(key="panels_row"):
    left, right = st.columns([3, 7], border=True)

    # ---------------- Left: documents ----------------
    with left:
        with st.container(key="synth_doc_area", height="stretch"):
            render_section_header("document", "Documents")

            doc_list_slot = st.container(key="synth_doc_list", height="stretch")
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
                        'Upload one or more PDFs below (two or more recommended), then click '
                        '<b>Generate literature review</b>.</div></div>',
                        unsafe_allow_html=True,
                    )

            # Uploader + generate button pinned at the bottom of the panel.
            uploaded_files = st.file_uploader(
                "Upload PDFs", type=["pdf"], accept_multiple_files=True,
                key="synth_uploader", label_visibility="collapsed",
                disabled=not ready,
            )
            generate_clicked = st.button(
                "Generate literature review", width="stretch", type="primary",
                disabled=not ready or not uploaded_files,
            )

            if generate_clicked:
                with doc_list_slot:
                    placeholders = {f.name: st.empty() for f in uploaded_files}
                    document_trees = ingest_pdfs(uploaded_files, placeholders=placeholders)
                st.session_state["synth_document_trees"] = document_trees

                if not document_trees:
                    show_error_toast("No documents processed successfully.")
                else:
                    if len(document_trees) == 1:
                        # A single paper can still get a "review", but a literature
                        # review is inherently comparative — flag this rather than
                        # silently producing a thin one-paper output.
                        show_caution_toast(
                            "Only one document was uploaded — a literature review is usually "
                            "comparative, so this one may read more like a summary. Add another "
                            "paper for a fuller comparison."
                        )
                    with st.spinner(f"Generating review across {len(document_trees)} document(s) "
                                     f"(this can take 30-60s across several synthesis steps)..."):
                        try:
                            llm = get_llm()
                            result = generate_literature_review(llm, document_trees)
                            st.session_state["synth_review"] = result["review_text"]
                            st.session_state.pop("synth_pdf_bytes", None)
                        except Exception as e:
                            show_error_toast(f"Something went wrong generating the review: {e}")
                st.rerun()

    # ---------------- Right: review ----------------
    with right:
        with st.container(key="synth_result_area", height="stretch"):
            render_section_header("synthesize", "Review")
            review_text = st.session_state.get("synth_review")

            result_body = st.container(key="synth_result_body", height="stretch")
            with result_body:
                if not review_text:
                    st.markdown(
                        '<div class="pt-empty-fill"><div class="pt-caution-box">'
                        '⚠ Add at least one file on the left (two or more recommended) '
                        'to generate the literature review.</div></div>',
                        unsafe_allow_html=True,
                    )
                else:
                    format_choice = st.selectbox("View as", ["Formatted", "Download PDF", "Copy as text"])

                    if format_choice == "Formatted":
                        st.markdown(review_text)

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
                        escaped = _html.escape(copyable)
                        st.markdown(f"""
                            <textarea id="pt-copy-src" style="position:absolute; left:-9999px;">{escaped}</textarea>
                            <button onclick="navigator.clipboard.writeText(document.getElementById('pt-copy-src').value);
                                              this.innerText='✅ Copied!';
                                              setTimeout(() => this.innerText='📋 Copy to clipboard', 1500);"
                                    style="padding:0.5rem 1rem;border-radius:0.5rem;border:1px solid #f97316;
                                           background:transparent;color:#f97316;cursor:pointer;font-weight:600;">
                                📋 Copy to clipboard
                            </button>
                        """, unsafe_allow_html=True)