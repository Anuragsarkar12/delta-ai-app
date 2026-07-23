import logging
import chromadb
from typing import List, Dict, Any, Tuple
from src.canonical.model import CanonicalDocument
from src.delta.model import DeltaReport
from rank_bm25 import BM25Okapi
import string

logger = logging.getLogger(__name__)

def tokenize(text: str) -> List[str]:
    """Simple tokenizer for BM25: lowercase, remove punctuation, split by whitespace."""
    text = text.lower()
    text = text.translate(str.maketrans('', '', string.punctuation))
    return text.split()

class DocumentIndex:
    def __init__(self, persist_directory: str = "data/chroma"):
        """
        Initializes a Hybrid Retriever using ChromaDB (Semantic/Vector) and BM25 (Keyword/Lexical).
        """
        logger.info(f"Initializing Hybrid Index (ChromaDB + BM25) at {persist_directory}")
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(name="delta_chat_context")
        
        # In-memory stores for BM25
        self.corpus: List[str] = []
        self.metadatas: List[Dict[str, Any]] = []
        self.bm25: BM25Okapi = None

    def index_document(self, doc: CanonicalDocument):
        logger.info(f"Indexing Document: {doc.pid}")
        documents = []
        metadatas = []
        ids = []
        
        for page in doc.pages:
            page_text = "\n".join([elem.content for elem in page.elements if elem.content])
            if not page_text.strip():
                continue
                
            documents.append(page_text)
            metadatas.append({
                "source": "document",
                "pid": doc.pid,
                "page_number": page.page_number
            })
            ids.append(f"{doc.pid}_page_{page.page_number}")
            
        if documents:
            self.collection.upsert(documents=documents, metadatas=metadatas, ids=ids)
            self.corpus.extend(documents)
            self.metadatas.extend(metadatas)
            logger.debug(f"Indexed {len(documents)} chunks for {doc.pid}")

    def index_delta_report(self, report: DeltaReport):
        logger.info(f"Indexing Delta Report for {report.base_pid} -> {report.revised_pid}")
        documents = []
        metadatas = []
        ids = []
        
        for item in report.changes:
            doc_text = f"Change Type: {item.change_type.value}\nDescription: {item.description}\nLocation: Page {item.page_number}"
            documents.append(doc_text)
            metadatas.append({
                "source": "delta_report",
                "base_pid": report.base_pid,
                "revised_pid": report.revised_pid,
                "page_number": item.page_number,
                "confidence": item.confidence.value
            })
            ids.append(f"delta_{item.id}")
            
        if documents:
            self.collection.upsert(documents=documents, metadatas=metadatas, ids=ids)
            self.corpus.extend(documents)
            self.metadatas.extend(metadatas)
            logger.debug(f"Indexed {len(documents)} delta items.")

    def finalize_index(self):
        """Must be called after all documents are added to build the BM25 model."""
        logger.info("Building BM25 keyword index...")
        tokenized_corpus = [tokenize(doc) for doc in self.corpus]
        if tokenized_corpus:
            self.bm25 = BM25Okapi(tokenized_corpus)

    def retrieve(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieves context using Reciprocal Rank Fusion (RRF) over ChromaDB and BM25.
        """
        # 1. Semantic Search (ChromaDB)
        chroma_results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        chroma_ranked = []
        if chroma_results['documents']:
            for idx, content in enumerate(chroma_results['documents'][0]):
                # Using the content as the unique key for RRF
                chroma_ranked.append(content)
                
        # 2. Keyword Search (BM25)
        bm25_ranked = []
        if self.bm25:
            tokenized_query = tokenize(query)
            bm25_scores = self.bm25.get_scores(tokenized_query)
            # Get top indices sorted by score descending
            top_bm25_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:n_results]
            for idx in top_bm25_indices:
                if bm25_scores[idx] > 0: # Only include if there is an actual match
                    bm25_ranked.append(self.corpus[idx])
                    
        # 3. Reciprocal Rank Fusion (RRF)
        # RRF_Score = 1 / (k + rank)
        k = 60
        rrf_scores = {}
        
        for rank, content in enumerate(chroma_ranked):
            rrf_scores[content] = rrf_scores.get(content, 0) + (1.0 / (k + rank))
            
        for rank, content in enumerate(bm25_ranked):
            rrf_scores[content] = rrf_scores.get(content, 0) + (1.0 / (k + rank))
            
        # Sort by RRF score
        sorted_fused = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:n_results]
        
        # 4. Map back to metadata and format
        formatted_results = []
        for content, score in sorted_fused:
            # Find the metadata for this content (inefficient for massive DBs, but fine for in-memory)
            try:
                idx = self.corpus.index(content)
                meta = self.metadatas[idx]
                formatted_results.append({
                    "content": content,
                    "metadata": meta,
                    "rrf_score": score
                })
            except ValueError:
                continue
                
        logger.info(f"Hybrid retrieval complete. Found {len(formatted_results)} results.")
        return formatted_results
