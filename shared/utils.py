"""Shared helpers used across Ask, Discover, and Synthesize pages."""
import os
import tempfile
import time
import streamlit as st
from langchain_groq import ChatGroq
from pageindex import PageIndexClient

GROQ_MODEL = "openai/gpt-oss-120b"


# ---------------------------------------------------------------------------
# Global styling: red = error, orange = caution, everywhere in the app.
# ---------------------------------------------------------------------------

def inject_global_css():
    """App-wide CSS: consistent red/orange semantics, disabled-panel look,
    and fixed-position containers for toasts + key-status badges."""
    st.markdown("""
    <style>
    /* Streamlit's own alert boxes stay on-brand too */
    div[data-testid="stAlert"][data-baseweb="notification"]:has(svg[color="rgb(255, 43, 43)"]) { }

    .pt-toast-container {
        position: fixed;
        top: 4.25rem;
        right: 1.25rem;
        z-index: 999999;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        max-width: 340px;
        pointer-events: none;
    }
    .pt-toast {
        padding: 0.7rem 1rem;
        border-radius: 0.5rem;
        color: #fff;
        font-size: 0.85rem;
        line-height: 1.35;
        box-shadow: 0 4px 14px rgba(0,0,0,0.3);
        animation: pt-fade-in 0.25s ease-out;
        pointer-events: auto;
    }
    .pt-toast-error { background-color: #dc2626; border-left: 4px solid #7f1d1d; }
    .pt-toast-caution { background-color: #f97316; border-left: 4px solid #9a3412; }
    @keyframes pt-fade-in {
        from { opacity: 0; transform: translateY(-8px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .pt-badge-row {
        position: fixed;
        top: 3.35rem;
        right: 1.25rem;
        z-index: 999998;
        display: flex;
        gap: 0.4rem;
    }
    .pt-badge {
        padding: 0.25rem 0.6rem;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 600;
        white-space: nowrap;
        box-shadow: 0 2px 6px rgba(0,0,0,0.25);
    }
    .pt-badge-ok { background-color: #15803d; color: #fff; }
    .pt-badge-missing { background-color: #f97316; color: #fff; }

    .pt-panel-header {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        margin-bottom: 0.15rem;
    }
    .pt-panel-header img, .pt-panel-header svg { width: 28px; height: 28px; flex-shrink: 0; }
    .pt-panel-header .pt-title { font-size: 1.5rem; font-weight: 700; }
    .pt-tagline { color: #9ca3af; font-size: 0.95rem; margin-top: -0.2rem; margin-bottom: 0.75rem; }

    .pt-disabled-overlay {
        opacity: 0.4;
        pointer-events: none;
        filter: grayscale(40%);
    }
    .pt-caution-box {
        border: 1px solid #f97316;
        background: rgba(249, 115, 22, 0.08);
        border-radius: 0.6rem;
        padding: 1.25rem;
        text-align: center;
        color: #f97316;
        font-size: 0.95rem;
        margin: 1rem 0;
    }
    .pt-error-text { color: #dc2626; font-weight: 600; }
    .pt-caution-text { color: #f97316; font-weight: 600; }

    .pt-file-row {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.45rem 0.6rem;
        border: 1px solid rgba(128,128,128,0.25);
        border-radius: 0.5rem;
        margin-bottom: 0.4rem;
        font-size: 0.85rem;
    }
    .pt-file-icon { font-size: 1rem; }
    .pt-file-name { flex-grow: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    </style>
    """, unsafe_allow_html=True)


def show_error_toast(message: str):
    """Red top-right toast for errors."""
    inject_global_css()
    st.markdown(
        f'<div class="pt-toast-container"><div class="pt-toast pt-toast-error">⛔ {message}</div></div>',
        unsafe_allow_html=True,
    )


def show_caution_toast(message: str):
    """Orange top-right toast for cautions/warnings."""
    inject_global_css()
    st.markdown(
        f'<div class="pt-toast-container"><div class="pt-toast pt-toast-caution">⚠️ {message}</div></div>',
        unsafe_allow_html=True,
    )


def render_key_status_badges(need_groq: bool = True, need_pageindex: bool = False):
    """Small persistent top-right badges showing which keys are set — used
    instead of blocking the whole page when a key is missing."""
    inject_global_css()
    badges = []
    if need_groq:
        ok = bool(st.session_state.get("groq_api_key"))
        badges.append(f'<div class="pt-badge {"pt-badge-ok" if ok else "pt-badge-missing"}">'
                      f'{"✓ Groq" if ok else "⚠ Groq not set"}</div>')
    if need_pageindex:
        ok = bool(st.session_state.get("pageindex_api_key"))
        badges.append(f'<div class="pt-badge {"pt-badge-ok" if ok else "pt-badge-missing"}">'
                      f'{"✓ PageIndex" if ok else "⚠ PageIndex not set"}</div>')
    st.markdown(f'<div class="pt-badge-row">{"".join(badges)}</div>', unsafe_allow_html=True)


def keys_ready(need_groq: bool = True, need_pageindex: bool = False) -> bool:
    """Non-blocking check — returns True/False instead of stopping the page,
    so callers can render the full interface and just disable parts of it."""
    if need_groq and not st.session_state.get("groq_api_key"):
        return False
    if need_pageindex and not st.session_state.get("pageindex_api_key"):
        return False
    return True


def require_keys(need_groq: bool = True, need_pageindex: bool = False) -> bool:
    """Legacy blocking check (kept for any callers that still want a hard stop).
    Prefer keys_ready() + render_key_status_badges() for the split-pane pages."""
    missing = []
    if need_groq and not st.session_state.get("groq_api_key"):
        missing.append("Groq API key")
    if need_pageindex and not st.session_state.get("pageindex_api_key"):
        missing.append("PageIndex API key")

    if missing:
        missing_str = " and ".join(missing)
        show_caution_toast(
            f"{missing_str} not set. Please add "
            f"{'it' if len(missing) == 1 else 'them'} on the Integrations page first."
        )
        st.page_link("pages/1_Integrations.py", label="Go to Integrations", icon="🔑")
        return False
    return True


# ---------------------------------------------------------------------------
# Image-based headers (SVG icons instead of emoji logos)
# ---------------------------------------------------------------------------

ICONS = {
    "home": '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M4 11.5L12 4l8 7.5" stroke="#8b5cf6" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M6 10v9a1 1 0 0 0 1 1h3v-6h4v6h3a1 1 0 0 0 1-1v-9" stroke="#8b5cf6" stroke-width="1.8" stroke-linejoin="round"/>
    </svg>''',
    "ask": '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M4 5h16a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H9l-4 4v-4H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1z"
            stroke="#60a5fa" stroke-width="1.8" stroke-linejoin="round"/>
        <circle cx="8" cy="10.5" r="1" fill="#60a5fa"/>
        <circle cx="12" cy="10.5" r="1" fill="#60a5fa"/>
        <circle cx="16" cy="10.5" r="1" fill="#60a5fa"/>
    </svg>''',
    "discover": '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="10.5" cy="10.5" r="6.5" stroke="#34d399" stroke-width="1.8"/>
        <path d="M15.5 15.5L21 21" stroke="#34d399" stroke-width="1.8" stroke-linecap="round"/>
    </svg>''',
    "synthesize": '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M6 3h9l4 4v14a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z" stroke="#fbbf24" stroke-width="1.8" stroke-linejoin="round"/>
        <path d="M15 3v4a1 1 0 0 0 1 1h4" stroke="#fbbf24" stroke-width="1.8" stroke-linejoin="round"/>
        <path d="M8 12h8M8 15.5h8M8 18.5h5" stroke="#fbbf24" stroke-width="1.5" stroke-linecap="round"/>
    </svg>''',
    "key": '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="8" cy="15" r="4" stroke="#f472b6" stroke-width="1.8"/>
        <path d="M11.5 11.5L20 3M20 3v4h-4M20 3l-3 3" stroke="#f472b6" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>''',
}


def render_header(icon_key: str, title: str, tagline: str = ""):
    """Route header using an inline SVG image instead of an emoji."""
    inject_global_css()
    svg = ICONS.get(icon_key, "")
    st.markdown(
        f'<div class="pt-panel-header">{svg}<span class="pt-title">{title}</span></div>',
        unsafe_allow_html=True,
    )
    if tagline:
        st.markdown(f'<div class="pt-tagline">{tagline}</div>', unsafe_allow_html=True)


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


# ---------------------------------------------------------------------------
# PDF ingestion with live, per-file, in-place status (pie-spinner -> tick/cross)
# ---------------------------------------------------------------------------

_PIE_FRAMES = ["◴", "◷", "◶", "◵"]


def ingest_pdfs(uploaded_files, placeholders: dict = None, status_container=None) -> dict:
    """
    Saves Streamlit-uploaded PDFs to temp files, submits each to PageIndex,
    polls until all complete/fail, fetches trees, and returns document_trees
    in the same shape used throughout Ask/Synthesize: {doc_id: {filename, tree}}.
    Deletes temp files immediately after submission.

    If `placeholders` is given (dict of filename -> st.empty() placeholder),
    each file's status is updated *in place* (pie-spinner while processing,
    green tick on success, red cross on failure) instead of a scrolling log.
    `status_container` is kept for backward compatibility.
    """
    def _set(filename, html):
        if placeholders and filename in placeholders:
            placeholders[filename].markdown(html, unsafe_allow_html=True)
        elif status_container:
            status_container.write(filename + ": " + html)

    def _row(icon, filename, label):
        return (f'<div class="pt-file-row"><span class="pt-file-icon">{icon}</span>'
                f'<span class="pt-file-name">{filename}</span><span>{label}</span></div>')

    pi_client = get_pi_client()
    doc_records = {}

    for uploaded_file in uploaded_files:
        _set(uploaded_file.name, _row("⏳", uploaded_file.name, "uploading..."))
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
    frame = 0
    while pending:
        for doc_id in list(pending):
            status_result = pi_client.get_document(doc_id)
            status = status_result.get("status")
            doc_records[doc_id]["status"] = status
            filename = doc_records[doc_id]["filename"]
            if status in ("completed",):
                _set(filename, _row("✅", filename, "completed"))
                pending.remove(doc_id)
            elif status in ("failed", "error"):
                _set(filename, _row("❌", filename, "failed"))
                pending.remove(doc_id)
            else:
                _set(filename, _row(_PIE_FRAMES[frame % len(_PIE_FRAMES)], filename, status or "processing"))
        if pending:
            time.sleep(5)
            frame += 1

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
