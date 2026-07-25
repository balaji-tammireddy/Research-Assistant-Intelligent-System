"""Ask module: RAG over uploaded papers with section-level citations.
Ported from ask/ask.ipynb — logic unchanged, llm is now passed in (BYOK)
instead of a module-level client built from env vars.
"""
import json
from langchain_core.messages import HumanMessage
from shared.utils import get_text_content

WINDOW_SIZE = 10


def compress_tree(nodes: list) -> list:
    out = []
    for n in nodes:
        entry = {
            "id": n["node_id"],
            "title": n["title"],
            "page": n.get("page_index", "?"),
            "sum": (n.get("summary") or n.get("prefix_summary") or "")[:200],
        }
        if n.get("nodes"):
            entry["children"] = compress_tree(n["nodes"])
        out.append(entry)
    return out


def llm_tree_search(llm, query: str, document_trees: dict) -> dict:
    compressed_all = [
        {"doc_id": doc_id, "filename": data["filename"], "tree": compress_tree(data["tree"])}
        for doc_id, data in document_trees.items()
    ]
    tree_json = json.dumps(compressed_all, separators=(",", ":"))

    prompt = f"""You are given a query and the tree structures of one or more research papers.
Identify which node_ids (across ANY of the documents) most likely contain the answer.
If the query requires comparing multiple papers, select relevant nodes from each relevant paper.
Think step by step about which sections are relevant.

Query: {query}

Documents:
{tree_json}

Reply only in this format:
{{
    "thinking": "<your step by step reasoning>",
    "node_list": [
        {{"doc_id": "...", "node_id": "..."}}
    ]
}}"""
    response = llm.invoke([HumanMessage(content=prompt)])
    return json.loads(get_text_content(response))


def fetch_full_text(selected_nodes: list, flat_index: list) -> list:
    lookup = {(n["doc_id"], n["node_id"]): n for n in flat_index}
    results = []
    for sel in selected_nodes:
        key = (sel["doc_id"], sel["node_id"])
        if key in lookup:
            results.append(lookup[key])
    return results


def is_answerable(search_result: dict) -> bool:
    return len(search_result.get("node_list", [])) > 0


def generate_answer(llm, query: str, full_sections: list, chat_history: list = None) -> dict:
    chat_history = chat_history or []

    # Build a deduplicated, numbered source list (dedupe by filename+section,
    # since the same section can be pulled in for multiple sub-claims).
    sources = []
    seen = {}
    for s in full_sections:
        key = (s["filename"], s["section_title"])
        if key not in seen:
            seen[key] = len(sources) + 1
            sources.append({
                "index": seen[key],
                "filename": s["filename"],
                "section_title": s["section_title"],
                "section_short": s["section_title"].split(" > ")[-1],
            })

    context = "\n\n".join(
        f"[{seen[(s['filename'], s['section_title'])]}] Source: {s['filename']}, Section: {s['section_title']}\n{s['text']}"
        for s in full_sections
    )
    history_text = "\n".join(f"{m['role']}: {m['content']}" for m in chat_history)

    prompt = f"""Answer the user's question using ONLY the context provided below. Do not use outside knowledge.
Each numbered block in the context (e.g. "[1] Source: ...") is a citable source.
Every claim you make must be followed by the matching bracketed number(s), e.g. "...as shown in the results [1]." or "[1][3]" for multiple sources.
Do not write out filenames or section names inline — use only the bracket numbers; the source list is shown separately below your answer.
If different sources disagree or provide nuance, reflect that clearly rather than oversimplifying.

Conversation so far:
{history_text}

Context:
{context}

Question: {query}

Answer:"""
    response = llm.invoke([HumanMessage(content=prompt)])

    # Group the numbered sources by paper for a clean, non-redundant source list.
    grouped = {}
    for s in sources:
        grouped.setdefault(s["filename"], []).append(s)

    # Kept for any callers still expecting the old flat string format.
    flat_citations = [f"{s['filename']} — {s['section_title']}" for s in sources]

    return {
        "answer": get_text_content(response),
        "citations": flat_citations,
        "sources": sources,
        "sources_by_paper": grouped,
    }


def fallback_response(query: str) -> dict:
    return {
        "answer": "No related documents found for this query.",
        "citations": [],
        "sources": [],
        "sources_by_paper": {},
        "needs_arxiv_fallback": True,
    }


def answer_query(llm, query: str, document_trees: dict, document_index: list, chat_history: list = None) -> dict:
    search_result = llm_tree_search(llm, query, document_trees)

    if not is_answerable(search_result):
        result = fallback_response(query)
        result["thinking"] = search_result.get("thinking", "")
        return result

    full_sections = fetch_full_text(search_result["node_list"], document_index)
    result = generate_answer(llm, query, full_sections, chat_history)
    result["needs_arxiv_fallback"] = False
    result["thinking"] = search_result.get("thinking", "")
    return result


def update_chat_history(llm, chat_history: list, new_user_msg: str, new_answer: str) -> list:
    """Sliding window: keeps last WINDOW_SIZE messages, summarizes overflow into one message."""
    chat_history = chat_history + [
        {"role": "user", "content": new_user_msg},
        {"role": "assistant", "content": new_answer},
    ]
    if len(chat_history) > WINDOW_SIZE:
        overflow = chat_history[:-WINDOW_SIZE]
        recent = chat_history[-WINDOW_SIZE:]
        overflow_text = "\n".join(f"{m['role']}: {m['content']}" for m in overflow)
        summary_prompt = f"Summarize this conversation excerpt in 2-3 concise sentences:\n{overflow_text}"
        summary_response = llm.invoke([HumanMessage(content=summary_prompt)])
        chat_history = [
            {"role": "system", "content": f"Earlier conversation summary: {get_text_content(summary_response)}"}
        ] + recent
    return chat_history
