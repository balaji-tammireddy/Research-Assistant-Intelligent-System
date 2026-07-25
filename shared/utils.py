"""Shared helpers used across Ask, Discover, and Synthesize pages."""
import os
import tempfile
import time
import streamlit as st
from langchain_groq import ChatGroq
from pageindex import PageIndexClient

GROQ_MODEL = "openai/gpt-oss-120b"


def get_text_content(response) -> str:
    """Handles both plain string and list-of-content-block LLM responses."""
    content = response.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return str(content)


def get_llm() -> ChatGroq:
    """Builds a ChatGroq client from the session's stored key. Fixed model."""
    return ChatGroq(api_key=st.session_state["groq_api_key"], model=GROQ_MODEL, temperature=0)


def get_pi_client() -> PageIndexClient:
    """Builds a PageIndex client from the session's stored key."""
    return PageIndexClient(api_key=st.session_state["pageindex_api_key"])


def require_keys(need_groq: bool = True, need_pageindex: bool = False) -> bool:
    """Shows an error and returns False if required keys are missing."""
    missing = []
    if need_groq and not st.session_state.get("groq_api_key"):
        missing.append("Groq API key")
    if need_pageindex and not st.session_state.get("pageindex_api_key"):
        missing.append("PageIndex API key")

    if missing:
        missing_str = " and ".join(missing)
        st.error(
            f"⚠️ {missing_str} not set. Please add "
            f"{'it' if len(missing) == 1 else 'them'} on the **Integrations** page first."
        )
        st.page_link("pages/1_Integrations.py", label="Go to Integrations", icon="🔑")
        return False
    return True


def ingest_pdfs(uploaded_files, status_container=None) -> dict:
    """
    Saves Streamlit-uploaded PDFs to temp files, submits each to PageIndex,
    polls until all complete/fail, fetches trees, and returns document_trees
    in the same shape used throughout Ask/Synthesize: {doc_id: {filename, tree}}.
    Deletes temp files immediately after submission.
    """
    pi_client = get_pi_client()
    doc_records = {}

    for uploaded_file in uploaded_files:
        if status_container:
            status_container.write(f"Uploading {uploaded_file.name}...")
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, uploaded_file.name)
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        try:
            result = pi_client.submit_document(temp_path)
            doc_records[result["doc_id"]] = {
                "filename": uploaded_file.name,
                "status": "submitted",
            }
        finally:
            os.remove(temp_path)

    pending = set(doc_records.keys())
    while pending:
        for doc_id in list(pending):
            status_result = pi_client.get_document(doc_id)
            status = status_result.get("status")
            doc_records[doc_id]["status"] = status
            if status_container:
                status_container.write(f"[{doc_records[doc_id]['filename']}] {status}")
            if status in ("completed", "failed"):
                pending.remove(doc_id)
        if pending:
            time.sleep(5)

    document_trees = {}
    failed = []
    for doc_id, info in doc_records.items():
        if info["status"] != "completed":
            failed.append(info["filename"])
            continue
        tree_result = pi_client.get_tree(doc_id, node_summary=True)
        document_trees[doc_id] = {
            "filename": info["filename"],
            "tree": tree_result.get("result", []),
        }

    if failed and status_container:
        status_container.warning(f"Failed to process: {', '.join(failed)}")

    return document_trees


def flatten_tree(nodes, doc_id, filename, parent_title=None):
    """Recursively flattens a PageIndex tree into a flat list of section records."""
    flat_nodes = []
    for node in nodes:
        summary = node.get("summary") or node.get("prefix_summary") or ""
        title = node["title"]
        full_title = f"{parent_title} > {title}" if parent_title else title
        flat_nodes.append({
            "doc_id": doc_id,
            "filename": filename,
            "node_id": node["node_id"],
            "section_title": full_title,
            "summary": summary,
            "page_index": node.get("page_index"),
            "text": node.get("text", ""),
        })
        children = node.get("nodes", [])
        if children:
            flat_nodes.extend(flatten_tree(children, doc_id, filename, parent_title=full_title))
    return flat_nodes


def build_document_index(document_trees: dict) -> list:
    """Builds the flat document_index used by Ask's fetch_full_text."""
    index = []
    for doc_id, data in document_trees.items():
        index.extend(flatten_tree(data["tree"], doc_id, data["filename"]))
    return index
