import os
import tempfile
import streamlit as st
from shared.utils import require_keys, get_llm, ingest_pdfs
from Synthesize.logic import generate_literature_review, export_review_to_pdf, get_copyable_text

st.set_page_config(page_title="PaperTrail — Synthesize", page_icon="📝")
st.title("📝 Synthesize")

if not require_keys(need_groq=True, need_pageindex=True):
    st.stop()

st.caption("Upload several papers to generate a structured literature review comparing them.")

uploaded_files = st.file_uploader(
    "Upload PDFs", type=["pdf"], accept_multiple_files=True, key="synth_uploader"
)

if uploaded_files and st.button("Generate literature review", type="primary"):
    with st.status("Processing documents...", expanded=True) as status:
        document_trees = ingest_pdfs(uploaded_files, status_container=status)
        if not document_trees:
            status.update(label="No documents processed successfully", state="error")
            st.stop()

        status.write(f"{len(document_trees)} document(s) indexed. Generating review "
                     f"(this can take 30-60s across several synthesis steps)...")
        try:
            llm = get_llm()
            result = generate_literature_review(llm, document_trees)
            st.session_state["synth_review"] = result["review_text"]
            status.update(label="Review ready", state="complete")
        except Exception as e:
            status.update(label="Generation failed", state="error")
            st.error(f"Something went wrong generating the review: {e}")

review_text = st.session_state.get("synth_review")

if review_text:
    st.divider()
    format_choice = st.radio("View as:", ["Formatted", "Download PDF", "Copy as text"], horizontal=True)

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
            )

    else:
        st.text_area("Copyable text", value=get_copyable_text(review_text), height=500)
