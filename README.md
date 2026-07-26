# 📄 PaperTrail

> **A citation-grounded research assistant for working with papers.**

PaperTrail is a research assistant built around three core tools—**Ask**, **Discover**, and **Synthesize**—sharing a common document-ingestion and Bring-Your-Own-Key (BYOK) layer. It emphasizes accuracy by using vectorless retrieval, parsing PDFs into structured section trees instead of generic text chunks.

---

## ✨ Key Features

### 1. 💬 Ask: Chat with Your Documents
Upload PDFs and get grounded answers with **exact section citations**.
- **Vectorless Retrieval:** Papers are parsed into a structured section tree. The LLM searches node IDs directly from titles and summaries, ensuring citations point to real, human-readable sections—not arbitrary chunk numbers.
- **Reliable Q&A:** Answers are strictly generated from the context with inline citations to eliminate hallucinated claims.
- **Cross-paper Comparison:** Supports comparison questions across multiple uploaded documents.
- **Smart History:** Keeps a sliding-window chat history, summarizing older turns rather than dropping them.

### 2. 🔍 Discover: Find Papers Worth Reading
Search arXiv with a strict LLM-powered relevance filter.
- **Disambiguation:** Ensures search terms (e.g., "transformers") are interpreted correctly in context (ML architecture vs. hardware).
- **True Relevance:** Rejects papers that merely *mention* a topic instead of being genuinely about it.
- **Smart Retry:** Includes a bounded retry with reworded search terms if the initial search results are insufficient.

### 3. ✍️ Synthesize: Turn a Stack of Papers into One Review
Generate a structured, comprehensive literature review from multiple papers.
- **Orchestrator-Worker Pipeline:** Built via LangGraph, this feature builds shared context across all uploaded papers.
- **Structured Output:** Automatically generates an Overview, Thematic Grouping, Methodology Comparison table, Key Findings Comparison (highlighting agreements/disagreements), and Gaps & Future Directions.
- **Exportable:** Download the final synthesized review as a nicely formatted PDF.

---

## 🏗️ Architecture & Design Decisions

- **Vectorless Retrieval:** Most RAG systems chunk documents and embed them, losing document structure. PaperTrail preserves the structure (via PageIndex), enabling precise citations.
- **One Fixed Model:** The LLM is locked to open-source models (like `openai/gpt-oss-120b` on Groq) to ensure the most reliable structured output and predictable behavior across all tools.
- **Privacy First (BYOK):** A Groq key powers the LLM, and a PageIndex key parses documents. Both live only in your current browser session. **No keys or documents are stored on a server or database.**

---

## 🛠️ Tech Stack

- **Frontend:** Streamlit
- **Orchestration:** LangChain & LangGraph
- **LLM:** Groq
- **Document Parsing:** PageIndex
- **Search Integration:** `arxiv`
- **PDF Generation:** ReportLab

---

## 🚀 Getting Started

### Prerequisites
- Python 3.12+
- API Keys: 
  - [Groq API Key](https://console.groq.com/keys)
  - [PageIndex API Key](https://pageindex.ai)

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd "Research Assistant Intelligent System"
   ```

2. **Set up a virtual environment:**
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On Mac/Linux:
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Running the Application

Start the Streamlit application:

```bash
streamlit run Home.py
```

Navigate to `http://localhost:8501` in your browser to start using PaperTrail.

---

## 🔒 Security & Privacy
All processing happens within your current browser session. We do not store your API keys or any uploaded documents.
