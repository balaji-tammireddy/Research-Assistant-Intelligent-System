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
        animation: pt-fade-in 0.2s ease-out, pt-fade-out 0.3s ease-in 2.5s forwards;
        pointer-events: auto;
    }
    .pt-toast-error { background-color: #dc2626; border-left: 4px solid #7f1d1d; }
    .pt-toast-caution { background-color: #f97316; border-left: 4px solid #9a3412; }
    @keyframes pt-fade-out {
        from { opacity: 1; transform: translateY(0); }
        to { opacity: 0; transform: translateY(-8px); }
    }
    @keyframes pt-fade-in {
        from { opacity: 0; transform: translateY(-8px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .pt-badge-row {
        position: fixed;
        top: 3.55rem;
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
    .pt-file-label { margin-left: auto; font-size: 0.75rem; color: #9ca3af; text-transform: capitalize; flex-shrink: 0; }

    /* -----------------------------------------------------------------
       Top bar: page header + inline caution message on the same row
    ----------------------------------------------------------------- */
    .pt-inline-caution {
        border: 1px solid #f97316;
        background: rgba(249, 115, 22, 0.08);
        border-radius: 0.5rem;
        padding: 0.55rem 0.9rem;
        color: #f97316;
        font-size: 0.85rem;
        line-height: 1.3;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }

    .block-container { padding-top: 3.4rem !important; padding-bottom: 1rem !important; }

    /* Small icon + label used for the panel sub-headers (Documents / Chat / Review) */
    .pt-section-header {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.5rem;
        font-weight: 600;
        font-size: 1.02rem;
        flex-shrink: 0;
    }
    .pt-section-header svg { width: 19px; height: 19px; flex-shrink: 0; }

    /* -----------------------------------------------------------------
       Status badges: replace ✅ / ❌ / ⏳ emoji with bordered-circle marks
    ----------------------------------------------------------------- */
    .pt-status-badge {
        width: 20px; height: 20px; min-width: 20px;
        border-radius: 50%;
        display: inline-flex; align-items: center; justify-content: center;
        border: 2px solid; font-size: 0.68rem; font-weight: 800; line-height: 1;
        flex-shrink: 0;
    }
    .pt-status-ok { border-color: #22c55e; color: #22c55e; }
    .pt-status-error { border-color: #dc2626; color: #dc2626; }
    .pt-status-processing { border-color: #f59e0b; color: #f59e0b; animation: pt-pulse 1.4s ease-in-out infinite; }
    @keyframes pt-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }

    /* -----------------------------------------------------------------
       Fixed-height, non-scrolling two-panel layout (Ask / Synthesize).
       The row height is capped to the viewport so the *window* never
       scrolls; only the inner panes (doc list / chat) scroll.
    ----------------------------------------------------------------- */
    .st-key-panels_row {
        height: calc(100vh - 11rem) !important;
        min-height: 520px;
        flex: none !important;
    }
    .st-key-panels_row > div { height: 100%; }
    .st-key-panels_row div[data-testid="stHorizontalBlock"] { height: 100%; }
    .st-key-panels_row div[data-testid="column"] { height: 100%; display: flex; }
    .st-key-panels_row div[data-testid="column"] [data-testid="stVerticalBlockBorderWrapper"],
    .st-key-panels_row div[data-testid="column"] [data-testid="stVerticalBlock"] {
        height: 100%; width: 100%; display: flex; flex-direction: column; min-height: 0;
    }
    /* keyed inner containers used as scrollable panes */
    .st-key-ask_doc_area, .st-key-ask_chat_area,
    .st-key-synth_doc_area, .st-key-synth_result_area {
        min-height: 0; overflow: hidden;
    }
    .st-key-ask_doc_list, .st-key-ask_chat_messages,
    .st-key-synth_doc_list, .st-key-synth_result_body {
        min-height: 0; overflow-y: auto;
    }

    /* Centers a caution message inside an otherwise-empty flexible area */
    .pt-empty-fill {
        flex: 1 1 auto;
        display: flex; align-items: center; justify-content: center;
        min-height: 0; text-align: center;
    }
    .pt-empty-fill .pt-caution-box { margin: 0; width: 100%; }
    /* Bounded, independently-scrolling sub-panes (doc list stays small,
       upload controls stay pinned below it, without a growing page) */
    .pt-scroll-pane {
        max-height: 260px;
        overflow-y: auto;
        margin-bottom: 0.6rem;
    }
    .st-key-ask_doc_list, .st-key-synth_doc_list {
        max-height: 280px !important;
        overflow-y: auto !important;
    }
    .st-key-ask_empty_fill, .st-key-synth_empty_fill,
    .st-key-ask_chat_messages, .st-key-synth_result_body {
        flex: 1 1 auto !important;
    }
    .st-key-ask_upload_controls, .st-key-synth_upload_controls {
        margin-top: auto !important;
    }
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


def show_info_toast(message: str):
    """Neutral top-right toast for in-progress status (e.g. 'Generating...')."""
    inject_global_css()
    st.markdown(
        f'<div class="pt-toast-container"><div class="pt-toast" '
        f'style="background-color:#4338ca;border-left:4px solid #312e81;">⏳ {message}</div></div>',
        unsafe_allow_html=True,
    )


def normalize_math_markdown(text: str) -> str:
    """LLMs often emit \\(...\\) / \\[...\\] LaTeX delimiters, which Streamlit's
    markdown renderer doesn't recognize (only $...$ / $$...$$ are). Normalize
    so formulas actually render instead of showing as raw text."""
    import re
    text = re.sub(r"\\\[(.+?)\\\]", r"$$\1$$", text, flags=re.S)
    text = re.sub(r"\\\((.+?)\\\)", r"$\1$", text, flags=re.S)
    return text


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
    "document": '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M7 3h7l5 5v13a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z"
            stroke="#60a5fa" stroke-width="1.8" stroke-linejoin="round"/>
        <path d="M14 3v5a1 1 0 0 0 1 1h5" stroke="#60a5fa" stroke-width="1.8" stroke-linejoin="round"/>
        <path d="M9 13h6M9 16.5h6M9 10h2" stroke="#60a5fa" stroke-width="1.4" stroke-linecap="round"/>
    </svg>''',
    "chat": '''<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M4 5h16a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H9l-4 4v-4H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1z"
            stroke="#60a5fa" stroke-width="1.8" stroke-linejoin="round"/>
        <circle cx="8" cy="10.5" r="1" fill="#60a5fa"/>
        <circle cx="12" cy="10.5" r="1" fill="#60a5fa"/>
        <circle cx="16" cy="10.5" r="1" fill="#60a5fa"/>
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


def render_section_header(icon_key: str, title: str):
    """Small in-panel header (e.g. Documents / Chat / Review) — SVG icon, no emoji."""
    inject_global_css()
    svg = ICONS.get(icon_key, "")
    st.markdown(f'<div class="pt-section-header">{svg}<span>{title}</span></div>', unsafe_allow_html=True)


def status_badge(kind: str) -> str:
    """Bordered-circle status mark: 'ok' (green tick), 'error' (red cross),
    'processing' (yellow exclamation) — used instead of ✅/❌/⏳ emoji."""
    symbol = {"ok": "✓", "error": "✕", "processing": "!"}.get(kind, "!")
    return f'<span class="pt-status-badge pt-status-{kind}">{symbol}</span>'


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

    def _row(kind, filename, label):
        return (f'<div class="pt-file-row">{status_badge(kind)}'
                f'<span class="pt-file-name">{filename}</span>'
                f'<span class="pt-file-label">{label}</span></div>')

    pi_client = get_pi_client()
    doc_records = {}

    for uploaded_file in uploaded_files:
        _set(uploaded_file.name, _row("processing", uploaded_file.name, "uploading..."))
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
            filename = doc_records[doc_id]["filename"]
            if status in ("completed",):
                _set(filename, _row("ok", filename, "completed"))
                pending.remove(doc_id)
            elif status in ("failed", "error"):
                _set(filename, _row("error", filename, "failed"))
                pending.remove(doc_id)
            else:
                _set(filename, _row("processing", filename, status or "processing"))
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


def copy_to_clipboard_button(text: str, label: str = "Copy to clipboard"):
    """A real, working copy button. st.markdown(unsafe_allow_html=True) does
    NOT reliably execute inline onclick JS — components.html runs in an
    actual sandboxed iframe with a working script context, which does."""
    import json as _json
    import uuid
    import streamlit.components.v1 as components
    safe_text = _json.dumps(text)
    uid = uuid.uuid4().hex[:8]
    components.html(f"""
        <button id="pt-copy-{uid}" style="
            background:transparent; color:#f97316; border:1px solid #f97316;
            border-radius:8px; padding:8px 16px; font-size:0.85rem;
            font-weight:600; cursor:pointer;">
            📋 {label}
        </button>
        <script>
        document.getElementById("pt-copy-{uid}").addEventListener("click", function() {{
            navigator.clipboard.writeText({safe_text});
            this.innerText = "✅ Copied!";
            setTimeout(() => this.innerText = "📋 {label}", 1500);
        }});
        </script>
    """, height=45)