"""Synthesize module: orchestrator-worker literature review generation
+ PDF export. Ported from Synthesize/synthesize.ipynb — node logic
unchanged. The LLM is injected into graph state as state["_llm"] (BYOK).
"""
import json
import re
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END
from typing import TypedDict
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from shared.utils import get_text_content, flatten_tree


def build_shared_context_node(state: dict) -> dict:
    llm = state["_llm"]
    papers_overview = []
    for doc_id, data in state["document_trees"].items():
        filename = data["filename"]
        sections = flatten_tree(data["tree"], doc_id, filename)
        section_summaries = "\n".join(
            f"  - {s['section_title']}: {s['summary'][:150]}" for s in sections[:15]
        )
        papers_overview.append(f"[{filename}]\n{section_summaries}")
    all_papers_text = "\n\n".join(papers_overview)

    prompt = f"""You are analyzing {len(state['document_trees'])} research papers to prepare
for writing a literature review. Based on their section summaries below, extract:

1. THEMES: 2-4 thematic groups that organize these papers (a paper can belong to
   multiple themes). For each theme, list which papers belong to it and why.
2. PER-PAPER KEY FACTS: for each paper, extract its core method/approach, key technique,
   evaluation approach, and main finding/conclusion, each in 1-2 sentences.

Papers:
{all_papers_text}

Reply ONLY in this JSON format, no other text:
{{
    "themes": [
        {{"name": "...", "papers": ["filename1.pdf", "filename2.pdf"], "description": "..."}}
    ],
    "paper_facts": [
        {{"filename": "...", "method": "...", "technique": "...", "evaluation": "...", "finding": "..."}}
    ]
}}"""
    response = llm.invoke([HumanMessage(content=prompt)])
    state["shared_context"] = json.loads(get_text_content(response))
    return state


def write_overview_node(state: dict) -> dict:
    llm = state["_llm"]
    ctx = state["shared_context"]
    prompt = f"""Write a concise Overview (roughly 100-150 words) for a literature review
covering {len(state['document_trees'])} papers. Themes identified: {json.dumps(ctx['themes'])}.

Describe the collective scope and what this review aims to synthesize. Do not list
papers individually by name and content — describe the overall landscape and focus areas."""
    response = llm.invoke([HumanMessage(content=prompt)])
    state["section_overview"] = get_text_content(response)
    return state


def write_thematic_grouping_node(state: dict) -> dict:
    llm = state["_llm"]
    ctx = state["shared_context"]
    prompt = f"""Write the "Thematic Grouping" section of a literature review (roughly 200-250 words).
Themes and paper assignments: {json.dumps(ctx['themes'])}

For each theme, write a short paragraph synthesizing what the papers in that theme
collectively contribute. Reference papers using (filename.pdf) format. Explain how
papers within a theme relate to each other, not just what each one does individually."""
    response = llm.invoke([HumanMessage(content=prompt)])
    state["section_thematic_grouping"] = get_text_content(response)
    return state


def write_methodology_comparison_node(state: dict) -> dict:
    llm = state["_llm"]
    ctx = state["shared_context"]
    prompt = f"""Write the "Methodology Comparison" section of a literature review.
Per-paper facts: {json.dumps(ctx['paper_facts'])}

Present this as a markdown table with columns: Paper | Method/Approach | Key Technique | Evaluation Approach.
Use (filename.pdf) to identify each paper in the Paper column.
If any paper's methodology doesn't fit cleanly into the table, add 1-2 sentences of
prose below the table to clarify. Keep the table concise — one row per paper."""
    response = llm.invoke([HumanMessage(content=prompt)])
    state["section_methodology"] = get_text_content(response)
    return state


def write_key_findings_node(state: dict) -> dict:
    llm = state["_llm"]
    ctx = state["shared_context"]
    prompt = f"""Write the "Key Findings Comparison" section of a literature review
(roughly 200-250 words). Per-paper facts: {json.dumps(ctx['paper_facts'])}

Explicitly identify where papers AGREE, DISAGREE, or COMPLEMENT each other's findings.
Reference papers using (filename.pdf) format. This is the most important section —
genuine synthesis and comparison, not parallel summaries of each paper in isolation."""
    response = llm.invoke([HumanMessage(content=prompt)])
    state["section_key_findings"] = get_text_content(response)
    return state


def write_gaps_node(state: dict) -> dict:
    llm = state["_llm"]
    ctx = state["shared_context"]
    prompt = f"""Based on this literature review's findings so far:

Themes: {json.dumps(ctx['themes'])}
Key Findings section: {state['section_key_findings']}

Write a "Gaps & Future Directions" section (roughly 150-200 words) — what do these
papers collectively NOT address? What open questions or limitations span across the
set? Reference papers using (filename.pdf) format where relevant."""
    response = llm.invoke([HumanMessage(content=prompt)])
    state["section_gaps"] = get_text_content(response)
    return state


def write_references_node(state: dict) -> dict:
    refs = [f"- {data['filename']}" for data in state["document_trees"].values()]
    state["section_references"] = "\n".join(refs)
    return state


def assemble_review_node(state: dict) -> dict:
    state["final_review"] = f"""# Literature Review

## Overview
{state['section_overview']}

## Thematic Grouping
{state['section_thematic_grouping']}

## Methodology Comparison
{state['section_methodology']}

## Key Findings Comparison
{state['section_key_findings']}

## Gaps & Future Directions
{state['section_gaps']}

## References
{state['section_references']}
"""
    return state


class SynthesizeState(TypedDict):
    _llm: object
    document_trees: dict
    shared_context: dict
    section_overview: str
    section_thematic_grouping: str
    section_methodology: str
    section_key_findings: str
    section_gaps: str
    section_references: str
    final_review: str


def build_synthesize_graph():
    graph = StateGraph(SynthesizeState)
    graph.add_node("build_shared_context", build_shared_context_node)
    graph.add_node("write_overview", write_overview_node)
    graph.add_node("write_thematic_grouping", write_thematic_grouping_node)
    graph.add_node("write_methodology", write_methodology_comparison_node)
    graph.add_node("write_key_findings", write_key_findings_node)
    graph.add_node("write_gaps", write_gaps_node)
    graph.add_node("write_references", write_references_node)
    graph.add_node("assemble", assemble_review_node)

    graph.set_entry_point("build_shared_context")
    graph.add_edge("build_shared_context", "write_overview")
    graph.add_edge("write_overview", "write_thematic_grouping")
    graph.add_edge("write_thematic_grouping", "write_methodology")
    graph.add_edge("write_methodology", "write_key_findings")
    graph.add_edge("write_key_findings", "write_gaps")
    graph.add_edge("write_gaps", "write_references")
    graph.add_edge("write_references", "assemble")
    graph.add_edge("assemble", END)
    return graph.compile()


def generate_literature_review(llm, document_trees: dict) -> dict:
    graph = build_synthesize_graph()
    initial_state = {
        "_llm": llm,
        "document_trees": document_trees,
        "shared_context": {},
        "section_overview": "",
        "section_thematic_grouping": "",
        "section_methodology": "",
        "section_key_findings": "",
        "section_gaps": "",
        "section_references": "",
        "final_review": "",
    }
    result = graph.invoke(initial_state)
    return {"review_text": result["final_review"], "shared_context": result["shared_context"]}


# ---------- PDF export ----------

def sanitize_text(text: str) -> str:
    replacements = {
        '\u2011': '-', '\u2010': '-', '\u2012': '-',
        '\u2013': '-', '\u2014': '--',
        '\u2018': "'", '\u2019': "'",
        '\u201c': '"', '\u201d': '"',
        '\u2026': '...',
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    return ''.join(ch if _encodable(ch) else '-' for ch in text)


def _encodable(ch: str) -> bool:
    try:
        ch.encode('latin-1')
        return True
    except UnicodeEncodeError:
        return False


def convert_inline_markdown(text: str) -> str:
    text = sanitize_text(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    return text


def strip_duplicate_heading(paragraph_text: str, heading: str) -> str:
    cleaned = paragraph_text.strip()
    for variant in (heading, f"**{heading}**"):
        if cleaned.startswith(variant):
            cleaned = cleaned[len(variant):].strip()
    return cleaned


def parse_markdown_table(table_lines: list) -> list:
    rows = []
    for line in table_lines:
        line = line.strip()
        if not line or set(line) <= {"|", "-", " ", ":"}:
            continue
        rows.append([c.strip() for c in line.strip("|").split("|")])
    return rows


def export_review_to_pdf(review_text: str, output_path: str, title: str = "Literature Review") -> str:
    doc = SimpleDocTemplate(output_path, pagesize=letter, topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    styles = getSampleStyleSheet()

    heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'],
                                    textColor=colors.HexColor('#371e77'), spaceBefore=16, spaceAfter=8)
    title_style = ParagraphStyle('CustomTitle', parent=styles['Title'], textColor=colors.HexColor('#1C033C'))
    body_style = ParagraphStyle('CustomBody', parent=styles['Normal'], spaceAfter=8, leading=15)
    cell_style = ParagraphStyle('CellText', parent=styles['Normal'], fontSize=8, leading=10)
    bullet_style = ParagraphStyle('Bullet', parent=styles['Normal'], leftIndent=14, spaceAfter=4)

    story = [Paragraph(sanitize_text(title), title_style), Spacer(1, 12)]
    lines = review_text.split("\n")
    i = 0
    paragraph_buffer = []
    current_heading = ""
    just_added_heading = False

    def flush_paragraph():
        nonlocal just_added_heading
        if paragraph_buffer:
            text = strip_duplicate_heading(" ".join(paragraph_buffer).strip(), current_heading)
            if text:
                story.append(Paragraph(convert_inline_markdown(text), body_style))
                just_added_heading = False
            paragraph_buffer.clear()

    while i < len(lines):
        line = lines[i]
        if line.startswith("## "):
            new_heading = line.replace("## ", "").strip()
            if new_heading == current_heading and just_added_heading:
                i += 1
                continue
            flush_paragraph()
            current_heading = new_heading
            story.append(Paragraph(sanitize_text(current_heading), heading_style))
            just_added_heading = True
        elif line.startswith("# "):
            i += 1
            continue
        elif line.strip().startswith("- "):
            flush_paragraph()
            story.append(Paragraph(f"• {convert_inline_markdown(line.strip()[2:])}", bullet_style))
            just_added_heading = False
        elif line.strip().startswith("|"):
            flush_paragraph()
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            raw_rows = parse_markdown_table(table_lines)
            if raw_rows:
                wrapped_rows = [[Paragraph(convert_inline_markdown(c), cell_style) for c in row] for row in raw_rows]
                num_cols = len(raw_rows[0])
                col_width = (letter[0] - 1.5 * inch) / num_cols
                t = Table(wrapped_rows, colWidths=[col_width] * num_cols, hAlign='LEFT')
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 4),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ]))
                story.append(t)
                story.append(Spacer(1, 10))
            just_added_heading = False
            continue
        elif line.strip() == "":
            flush_paragraph()
        else:
            paragraph_buffer.append(line)
        i += 1

    flush_paragraph()
    doc.build(story)
    return output_path


def get_copyable_text(review_text: str) -> str:
    return review_text
