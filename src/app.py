import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv

from src.observability.logging import setup_logging
from src.observability.tracing import setup_tracing
from src.ingest.pdf_native import NativePDFParser
from src.ingest.pdf_scanned import ScannedPDFParser
from src.delta.engine import DeltaEngine
from src.chat.index import DocumentIndex
from src.chat.answer import ChatBot

# Setup environment and observability
load_dotenv()
logger = setup_logging()
setup_tracing()

app = FastAPI(title="Delta Chat API")

# Initialize core services
# Using an ephemeral ChromaDB for the web app to avoid persistence lock issues, 
# or a specific web-app path.
os.makedirs("data/chroma_webapp", exist_ok=True)
doc_index = DocumentIndex(persist_directory="data/chroma_webapp")
chat_bot = ChatBot(index=doc_index)
delta_engine = DeltaEngine()

class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    answer: str
    citations: list[str]

@app.post("/api/upload")
async def upload_files(
    base_file: UploadFile = File(...),
    revised_file: UploadFile = File(...)
):
    """
    Accepts two PDFs, parses them, computes the delta, indexes everything for RAG,
    and returns the structured delta report.
    """
    logger.info("Received file upload request.")
    
    os.makedirs("data/uploads", exist_ok=True)
    base_path = f"data/uploads/base_{base_file.filename}"
    revised_path = f"data/uploads/revised_{revised_file.filename}"
    
    with open(base_path, "wb") as buffer:
        shutil.copyfileobj(base_file.file, buffer)
    with open(revised_path, "wb") as buffer:
        shutil.copyfileobj(revised_file.file, buffer)
        
    try:
        # 1. Parse (Assuming Native PDF for simplicity in this endpoint, 
        # but could fallback to Scanned based on exceptions)
        parser = NativePDFParser()
        base_doc = parser.parse(base_path, pid="Base_Document")
        revised_doc = parser.parse(revised_path, pid="Revised_Document")
        
        # 2. Compute Delta
        report = delta_engine.compute_delta(base_doc, revised_doc)
        
        # 3. Index for RAG
        doc_index.index_document(base_doc)
        doc_index.index_document(revised_doc)
        doc_index.index_delta_report(report)
        doc_index.finalize_index() # Build BM25
        
        return report.model_dump()
        
    except Exception as e:
        logger.error(f"Processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    """
    Queries the RAG engine over the indexed documents and delta report.
    """
    try:
        response = chat_bot.ask(req.query)
        return ChatResponse(answer=response.answer, citations=response.citations)
    except Exception as e:
        logger.error(f"Chat failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate answer.")

# Serve static frontend files (HTML/CSS/JS)
os.makedirs("static", exist_ok=True)
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    logger.info("Starting Web Server...")
    uvicorn.run("src.app:app", host="0.0.0.0", port=8000, reload=True)
