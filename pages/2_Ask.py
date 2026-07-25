import streamlit as st
from shared.utils import require_keys, get_llm, ingest_pdfs, build_document_index
from ask.logic import answer_query, update_chat_history

st.set_page_config(page_title="PaperTrail — Ask", page_icon="💬")
st.title("💬 Ask")

if not require_keys(need_groq=True, need_pageindex=True):
    st.stop()

st.caption("Upload research papers and ask questions. Answers cite the exact section they came from.")

if "ask_document_trees" not in st.session_state:
    st.session_state["ask_document_trees"] = {}
    st.session_state["ask_document_index"] = []
    st.session_state["ask_chat_history"] = []

uploaded_files = st.file_uploader(
    "Upload PDFs", type=["pdf"], accept_multiple_files=True, key="ask_uploader"
)

if uploaded_files and st.button("Process documents"):
    with st.status("Processing documents...", expanded=True) as status:
        document_trees = ingest_pdfs(uploaded_files, status_container=status)
        st.session_state["ask_document_trees"] = document_trees
        st.session_state["ask_document_index"] = build_document_index(document_trees)
        st.session_state["ask_chat_history"] = []
        status.update(label=f"Ready — {len(document_trees)} document(s) indexed", state="complete")

document_trees = st.session_state["ask_document_trees"]

if not document_trees:
    st.info("Upload at least one PDF and click **Process documents** to start chatting.")
    st.stop()

st.success(f"{len(document_trees)} document(s) loaded: " + ", ".join(d["filename"] for d in document_trees.values()))

# Render existing chat history
for msg in st.session_state["ask_chat_history"]:
    if msg["role"] in ("user", "assistant"):
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg.get("citations"):
                st.caption("Sources: " + " · ".join(f"`{c}`" for c in msg["citations"]))

question = st.chat_input("Ask a question about your uploaded papers...")

if question:
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
                if result["citations"]:
                    st.caption("Sources: " + " · ".join(f"`{c}`" for c in result["citations"]))
            except Exception as e:
                st.error(f"Something went wrong answering that question: {e}")
                result = None

    if result:
        st.session_state["ask_chat_history"] = update_chat_history(
            get_llm(), st.session_state["ask_chat_history"], question, result["answer"]
        )
        # store citations alongside the last assistant turn for re-rendering
        st.session_state["ask_chat_history"][-1]["citations"] = result["citations"]
