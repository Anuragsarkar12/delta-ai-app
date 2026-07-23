import logging
import litellm
from typing import List, Dict, Any
from pydantic import BaseModel, Field
import instructor
from src.chat.index import DocumentIndex

logger = logging.getLogger(__name__)
client = instructor.from_litellm(litellm.completion)

class ChatAnswer(BaseModel):
    answer: str = Field(description="The answer to the user's question, completely grounded in the provided context.")
    citations: List[str] = Field(description="A list of citations supporting the answer. Format: '[Source Name, Page X]'")

class ChatBot:
    def __init__(self, index: DocumentIndex, model_name: str = "groq/mixtral-8x7b-32768"):
        self.index = index
        self.model_name = model_name
        
    def ask(self, query: str) -> ChatAnswer:
        logger.info(f"Received query: '{query}'")
        
        # 1. Retrieve context
        contexts = self.index.retrieve(query, n_results=5)
        
        if not contexts:
            return ChatAnswer(
                answer="I could not find any relevant information in the documents or the delta report to answer this question.",
                citations=[]
            )
            
        # 2. Format context for the LLM
        context_block = ""
        for i, ctx in enumerate(contexts):
            meta = ctx["metadata"]
            if meta["source"] == "delta_report":
                source_name = f"Delta Report (Page {meta.get('page_number', 'N/A')})"
            else:
                source_name = f"Document PID {meta.get('pid')} (Page {meta.get('page_number', 'N/A')})"
                
            context_block += f"--- Source {i+1}: {source_name} ---\n{ctx['content']}\n\n"
            
        # 3. Construct strict RAG prompt
        system_prompt = (
            "You are an engineering assistant answering questions about document revisions.\n"
            "You must follow these rules strictly:\n"
            "1. Answer the user's query ONLY using the information provided in the Context Block below.\n"
            "2. If the answer is not contained in the context, you must state 'I cannot answer this based on the provided documents.' Do not hallucinate.\n"
            "3. Provide strict citations in the `citations` list field matching the 'Source X' names from the context block.\n\n"
            "Context Block:\n"
            f"{context_block}"
        )
        
        try:
            logger.debug(f"Sending prompt to {self.model_name}...")
            response = client.chat.completions.create(
                model=self.model_name,
                response_model=ChatAnswer,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                temperature=0.0
            )
            logger.info("Successfully generated grounded answer.")
            return response
            
        except Exception as e:
            logger.error(f"Chat generation failed: {str(e)}")
            raise
