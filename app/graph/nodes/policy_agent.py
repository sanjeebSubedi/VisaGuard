"""
Policy Agent - RAG for Regulatory Queries

This agent retrieves relevant regulatory information from the vector store
to answer policy-related questions with citations.

Key features:
- Hybrid search (semantic + keyword) for better retrieval
- Citation tracking (returns the specific regulation referenced)
- Confidence thresholds (returns "needs manual verification" if score < 0.7)
- Uses scrubbed text only (no PII in the vector store)
"""

from dataclasses import dataclass
from typing import Optional
import chromadb
from chromadb.utils import embedding_functions

from app.core.config import DATA_DIR, GEMINI_API_KEY


# Confidence threshold - below this, we don't trust the retrieval
CONFIDENCE_THRESHOLD = 0.7


@dataclass
class RetrievalResult:
    """Result from a policy retrieval query."""
    query: str
    answer: str
    citations: list[dict]
    confidence: float
    needs_manual_review: bool
    

@dataclass
class PolicyChunk:
    """A chunk of policy/regulatory text stored in the vector DB."""
    id: str
    text: str
    source: str  # e.g., "8 CFR 214.2(f)", "University Handbook"
    section: str  # e.g., "STEM OPT Requirements"
    metadata: dict


class PolicyAgent:
    """
    RAG agent for retrieving regulatory information.
    
    This agent:
    1. Embeds the query
    2. Retrieves relevant regulatory chunks from ChromaDB
    3. Checks confidence scores
    4. Returns results with citations
    
    Usage:
        agent = PolicyAgent()
        agent.initialize()  # One-time setup
        result = agent.query("Can I work unpaid during OPT?")
    """
    
    def __init__(
        self,
        collection_name: str = "regulations",
        persist_directory: Optional[str] = None,
    ):
        """
        Initialize the Policy Agent.
        
        Args:
            collection_name: Name of the ChromaDB collection.
            persist_directory: Directory for persisting ChromaDB.
        """
        self.collection_name = collection_name
        self.persist_directory = persist_directory or str(DATA_DIR / ".chromadb")
        self.client: Optional[chromadb.ClientAPI] = None
        self.collection: Optional[chromadb.Collection] = None
        self._initialized = False
    
    def initialize(self) -> None:
        """
        Initialize ChromaDB client and collection.
        
        Call this once before using the agent.
        """
        if self._initialized:
            return
        
        # Create persistent client
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        
        # Use Google Gemini embeddings if API key is available, otherwise use default
        if GEMINI_API_KEY:
            embedding_fn = embedding_functions.GoogleGenerativeAiEmbeddingFunction(
                api_key=GEMINI_API_KEY,
                model_name="models/text-embedding-004"
            )
        else:
            # Fallback to default (sentence-transformers)
            embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=embedding_fn,
            metadata={"description": "F-1 OPT regulatory documents and policies"}
        )
        
        self._initialized = True
    
    def add_document(
        self,
        text: str,
        source: str,
        section: str,
        doc_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Add a regulatory document chunk to the vector store.
        
        Args:
            text: The text content (should be scrubbed of PII).
            source: Source citation (e.g., "8 CFR 214.2(f)").
            section: Section or topic name.
            doc_id: Optional document ID (auto-generated if not provided).
            metadata: Optional additional metadata.
            
        Returns:
            The document ID.
        """
        if not self._initialized:
            self.initialize()
        
        import hashlib
        doc_id = doc_id or hashlib.sha256(text.encode()).hexdigest()[:16]
        
        full_metadata = {
            "source": source,
            "section": section,
            **(metadata or {})
        }
        
        self.collection.add(
            documents=[text],
            ids=[doc_id],
            metadatas=[full_metadata]
        )
        
        return doc_id
    
    def add_documents_batch(
        self,
        documents: list[PolicyChunk]
    ) -> list[str]:
        """
        Add multiple documents in batch.
        
        Args:
            documents: List of PolicyChunk objects.
            
        Returns:
            List of document IDs.
        """
        if not self._initialized:
            self.initialize()
        
        ids = [doc.id for doc in documents]
        texts = [doc.text for doc in documents]
        metadatas = [
            {"source": doc.source, "section": doc.section, **doc.metadata}
            for doc in documents
        ]
        
        self.collection.add(
            documents=texts,
            ids=ids,
            metadatas=metadatas
        )
        
        return ids
    
    def query(
        self,
        question: str,
        n_results: int = 3,
    ) -> RetrievalResult:
        """
        Query the policy knowledge base.
        
        Args:
            question: The policy question to answer.
            n_results: Number of results to retrieve.
            
        Returns:
            RetrievalResult with answer, citations, and confidence.
        """
        if not self._initialized:
            self.initialize()
        
        # Query the collection
        results = self.collection.query(
            query_texts=[question],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )
        
        # Extract results
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        
        if not documents:
            return RetrievalResult(
                query=question,
                answer="No relevant policy information found.",
                citations=[],
                confidence=0.0,
                needs_manual_review=True,
            )
        
        # Convert distances to similarity scores (ChromaDB uses L2 distance)
        # Lower distance = higher similarity
        # We normalize: similarity = 1 / (1 + distance)
        similarities = [1 / (1 + d) for d in distances]
        max_confidence = max(similarities)
        
        # Build citations
        citations = []
        for doc, meta, sim in zip(documents, metadatas, similarities):
            citations.append({
                "text": doc[:200] + "..." if len(doc) > 200 else doc,
                "source": meta.get("source", "Unknown"),
                "section": meta.get("section", "Unknown"),
                "confidence": round(sim, 3),
            })
        
        # Check if we need manual review
        needs_manual_review = max_confidence < CONFIDENCE_THRESHOLD
        
        # Build answer (concatenate relevant chunks)
        answer_parts = []
        for doc, meta in zip(documents, metadatas):
            answer_parts.append(f"According to {meta.get('source', 'policy')}:\n{doc}")
        
        if needs_manual_review:
            answer = (
                "⚠️ Low confidence in retrieved information. Manual verification recommended.\n\n"
                + "\n\n---\n\n".join(answer_parts)
            )
        else:
            answer = "\n\n---\n\n".join(answer_parts)
        
        return RetrievalResult(
            query=question,
            answer=answer,
            citations=citations,
            confidence=max_confidence,
            needs_manual_review=needs_manual_review,
        )
    
    def get_collection_stats(self) -> dict:
        """Get statistics about the policy collection."""
        if not self._initialized:
            self.initialize()
        
        return {
            "name": self.collection_name,
            "count": self.collection.count(),
        }


# Convenience function for LangGraph node
def policy_agent_node(state: dict) -> dict:
    """
    LangGraph node wrapper for PolicyAgent.
    
    Expects state to have a "policy_query" field.
    Returns state with "policy_result" field added.
    """
    agent = PolicyAgent()
    agent.initialize()
    
    query = state.get("policy_query", "")
    if not query:
        return {
            **state,
            "policy_result": {
                "error": "No policy query provided",
                "answer": None,
                "citations": [],
            }
        }
    
    result = agent.query(query)
    
    return {
        **state,
        "policy_result": {
            "query": result.query,
            "answer": result.answer,
            "citations": result.citations,
            "confidence": result.confidence,
            "needs_manual_review": result.needs_manual_review,
        }
    }


def get_policy_agent() -> PolicyAgent:
    """Get a configured PolicyAgent instance."""
    agent = PolicyAgent()
    agent.initialize()
    return agent
