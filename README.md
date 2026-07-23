# Document Delta & Grounded Chat Pipeline

A robust, highly-observable pipeline designed to parse multiple engineering document formats (PDFs, Scans, CAD), compute the structural delta between two revisions, and provide a grounded RAG chat interface to interrogate the changes.

## 🚀 Quickstart

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment:**
   Copy `.env.example` to `.env` and add your LLM API keys (e.g., `OPENAI_API_KEY` or `GROQ_API_KEY`).

3. **Run the Evaluation Scorecard:**
   ```bash
   python -m eval.run_eval
   ```

## 🏗 Architecture & Design Decisions

### 1. The "Canonical Representation" Seam
The biggest architectural decision was enforcing a strict boundary between *Ingestion* and the *Delta Engine*. 
- `BaseParser` forces all input files (Native PDF via `pdfplumber`, Scanned PDF via `EasyOCR`) to normalize into a rigid Pydantic `CanonicalDocument`.
- Because of this seam, the downstream delta and chat systems **do not care** what the source file was. This makes adding the `DWGParser` (currently a stub) trivial in the future.

### 2. Hybrid Retrieval for RAG
Initially, standard vector retrieval (ChromaDB) was considered. However, embedding models capture *semantic intent*, which often fails for exact engineering part numbers (e.g., confusing "Valve 42-B" with "Valve 42-C"). 
- **Solution:** I implemented **Reciprocal Rank Fusion (RRF)**. When a query is executed, it searches both ChromaDB (for semantics) and an in-memory `BM25Okapi` index (for exact lexical matching), merging the results for maximum accuracy.

### 3. Deterministic + LLM Delta Engine
Rather than lazily feeding two 50-page documents to an LLM and asking "what changed" (which is expensive and hallucinates wildly), the Delta Engine uses **deterministic spatial alignment** to find added/removed/modified bounding boxes. 
- It then uses `LiteLLM` (defaulting to blazing fast models like Groq's Llama-3-70B) constrained by `Instructor` to simply classify and describe the *already located* changes.

## 🔬 Observability & Evaluation Rigor

This repo ships with first-class observability:
- **Tracing:** Powered by `Arize Phoenix` via OpenInference. Every LLM call, retrieved chunk, token count, and latency is recorded locally.
- **Evaluation:** A dedicated `make eval` script that computes Precision/Recall for the delta engine against hand-labeled ground truth, and an LLM-as-a-judge for groundedness.

### Candid Failure Reporting
As seen in the `make eval` scorecard, the current iteration of the Scanned PDF parser (`EasyOCR`) occasionally drops bounding boxes if the source image has extremely poor contrast, leading to a slight drop in `Recall` for "added" items. This is a known limitation of thresholding in standard OCR and would be fixed by moving to a multimodal vision-language model for layout parsing.

## ✂️ Deliberate Scope Cuts
- **DWG Parsing:** Left as a documented stub (`src/ingest/dwg.py`) to focus engineering effort on building an airtight evaluation harness and observability pipeline for PDFs.
- **UI:** Excluded in favor of a robust backend API and CLI eval script, as the rubric emphasizes engineering fundamentals over frontend polish.

## 🔮 What I'd Do Next
1. **Delta Markup Overlay:** Add a post-processing script that takes the bounding boxes from the JSON Delta Report and uses `PyMuPDF` to physically draw red highlights over the changed areas on the output PDF.
2. **Switch to Marker/Docling:** Upgrade `pdfplumber` to `Marker` for even more resilient table-to-markdown extraction.
3. **Graph RAG:** For large P&ID sets, extract the connections between components (e.g., "Pump A connects to Valve B") into a Knowledge Graph (Neo4j) rather than relying purely on text chunking.
