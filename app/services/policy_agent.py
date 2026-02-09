import json
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
load_dotenv()  # Load GOOGLE_API_KEY from .env

import chromadb
from chromadb.config import Settings
from google import genai
from pydantic import BaseModel
from rank_bm25 import BM25Okapi


# Constants (matching policy_indexer.py)
DEFAULT_COLLECTION_NAME = "policy_corpus"
DEFAULT_DB_PATH = "data/vectordb"


class PolicyResult(BaseModel):
    """A single policy retrieval result."""
    
    id: str
    text: str
    citation: str
    title: str
    source_type: Literal["cfr", "handbook"]
    score: float
    metadata: dict = {}


class ExplanationResponse(BaseModel):
    """Response from the explain() method."""
    
    answer: str
    citations: list[PolicyResult]
    confidence: float
    conflicts: list[str] | None = None


class PolicyAgent:
    """
    RAG agent for policy retrieval and explanation.
    
    Usage:
        agent = PolicyAgent()
        results = agent.search("unemployment limit for STEM OPT")
        response = agent.explain("What is the unemployment limit for STEM OPT?")
    """
    
    def __init__(
        self,
        db_path: str = DEFAULT_DB_PATH,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        model_name: str = "gemini-3-flash-preview",
    ):
        self.db_path = Path(db_path)
        self.collection_name = collection_name
        self.model_name = model_name
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.db_path),
            settings=Settings(anonymized_telemetry=False),
        )
        
        # Get collection
        self.collection = self.client.get_collection(name=self.collection_name)
        
        # Initialize LLM (Google Gemini - native client)
        self.genai_client = genai.Client()  # Reads GEMINI_API_KEY from env
        self.model_name = model_name
        
        # Build BM25 index for hybrid search
        self._build_bm25_index()
    
    def _build_bm25_index(self) -> None:
        """Build BM25 index from all documents in collection."""
        # Get all documents
        results = self.collection.get(include=["documents", "metadatas"])
        
        self._doc_ids = results["ids"]
        self._doc_texts = results["documents"]
        self._doc_metadatas = results["metadatas"]
        
        # Tokenize for BM25
        tokenized = [doc.lower().split() for doc in self._doc_texts]
        self._bm25 = BM25Okapi(tokenized)
    
    def _hybrid_search(
        self,
        query: str,
        k: int = 5,
        alpha: float = 0.5,
    ) -> list[PolicyResult]:
        """
        Perform hybrid search combining vector similarity and BM25.
        
        Args:
            query: Search query
            k: Number of results to return
            alpha: Weight for vector search (1-alpha for BM25)
        
        Returns:
            List of PolicyResults sorted by combined score
        """
        # Vector search
        vector_results = self.collection.query(
            query_texts=[query],
            n_results=min(k * 2, len(self._doc_ids)),  # Get more for merging
            include=["documents", "metadatas", "distances"],
        )
        
        # BM25 search
        tokenized_query = query.lower().split()
        bm25_scores = self._bm25.get_scores(tokenized_query)
        
        # Normalize scores
        max_bm25 = max(bm25_scores) if max(bm25_scores) > 0 else 1
        
        # Combine scores using reciprocal rank fusion
        combined_scores = {}
        
        # Add vector results with their rank
        for i, doc_id in enumerate(vector_results["ids"][0]):
            # ChromaDB returns distances, lower is better
            # Convert to score (1 - distance for cosine)
            distance = vector_results["distances"][0][i]
            vector_score = 1 - distance
            combined_scores[doc_id] = alpha * vector_score
        
        # Add BM25 scores
        for i, doc_id in enumerate(self._doc_ids):
            normalized_bm25 = bm25_scores[i] / max_bm25
            if doc_id in combined_scores:
                combined_scores[doc_id] += (1 - alpha) * normalized_bm25
            else:
                combined_scores[doc_id] = (1 - alpha) * normalized_bm25
        
        # Sort and get top k
        sorted_ids = sorted(combined_scores.keys(), key=lambda x: combined_scores[x], reverse=True)[:k]
        
        # Build results
        results = []
        for doc_id in sorted_ids:
            idx = self._doc_ids.index(doc_id)
            metadata = self._doc_metadatas[idx]
            results.append(PolicyResult(
                id=doc_id,
                text=self._doc_texts[idx],
                citation=metadata.get("citation", ""),
                title=metadata.get("title", ""),
                source_type=metadata.get("source_type", "cfr"),
                score=combined_scores[doc_id],
                metadata=metadata,
            ))
        
        return results
    
    def search(
        self,
        query: str,
        k: int = 5,
        filters: dict | None = None,
    ) -> list[PolicyResult]:
        """
        Search for relevant policy documents.
        
        Args:
            query: Search query
            k: Number of results
            filters: Optional metadata filters
        
        Returns:
            List of PolicyResults
        """
        results = self._hybrid_search(query, k=k)
        
        # Apply filters if provided
        if filters:
            filtered = []
            for r in results:
                match = all(
                    r.metadata.get(key) == value
                    for key, value in filters.items()
                )
                if match:
                    filtered.append(r)
            results = filtered
        
        return results
    
    def explain(self, query: str, k: int = 5) -> ExplanationResponse:
        """
        Answer a policy question with citations.
        
        Args:
            query: Question to answer
            k: Number of sources to retrieve
        
        Returns:
            ExplanationResponse with answer and citations
        """
        # Retrieve relevant documents
        results = self.search(query, k=k)
        
        if not results:
            return ExplanationResponse(
                answer="No relevant policy information found.",
                citations=[],
                confidence=0.0,
            )
        
        # Build context for LLM
        context_parts = []
        for i, r in enumerate(results):
            context_parts.append(f"[{i+1}] {r.citation}: {r.text}")
        context = "\n\n".join(context_parts)
        
        # Generate response
        prompt = f"""You are an expert on F-1 visa regulations. Answer the following question using ONLY the provided policy sources. Cite sources using [1], [2], etc.

POLICY SOURCES:
{context}

QUESTION: {query}

Provide a clear, accurate answer citing the relevant sources. If the sources don't contain relevant information, say so."""
        
        response = self.genai_client.models.generate_content(
            model=self.model_name,
            contents=prompt
        )
        answer = response.text
        
        # Calculate confidence based on retrieval scores
        avg_score = sum(r.score for r in results) / len(results)
        confidence = min(avg_score, 1.0)
        
        return ExplanationResponse(
            answer=answer,
            citations=results,
            confidence=confidence,
        )
    
    def check_conflicts(self, clauses: list[str]) -> list[dict]:
        """
        Check for conflicts between policy clauses.
        
        Args:
            clauses: List of clause citations to check
        
        Returns:
            List of detected conflicts with explanations
        """
        # Get the text of specified clauses
        clause_texts = []
        for citation in clauses:
            for i, meta in enumerate(self._doc_metadatas):
                if meta.get("citation") == citation:
                    clause_texts.append({
                        "citation": citation,
                        "text": self._doc_texts[i],
                    })
                    break
        
        if len(clause_texts) < 2:
            return []
        
        # Ask LLM to detect conflicts
        clauses_formatted = "\n\n".join(
            f"[{c['citation']}]: {c['text']}" for c in clause_texts
        )
        
        prompt = f"""Analyze the following policy clauses for potential conflicts or contradictions. 
If there are conflicts, explain each one. If there are no conflicts, say "No conflicts detected."

CLAUSES:
{clauses_formatted}

Provide your analysis:"""
        
        response = self.genai_client.models.generate_content(
            model=self.model_name,
            contents=prompt
        )
        
        # Parse response (simple approach)
        if "no conflict" in response.text.lower():
            return []
        
        return [{"explanation": response.text}]
    
    def check_stem_eligible(self, cip_code: str) -> dict:
        """
        Check if a CIP code is STEM OPT eligible.
        
        This uses the JSON lookup table, not ChromaDB.
        
        Args:
            cip_code: CIP code to check (e.g., "11.0701")
        
        Returns:
            Dict with eligible status and title
        """
        stem_file = Path("data/policy_sources/dhs/stem_cip_codes.json")
        
        if not stem_file.exists():
            return {"eligible": False, "error": "STEM list not found"}
        
        with open(stem_file) as f:
            stem_codes = json.load(f)
        
        # Normalize the code format
        normalized = cip_code.strip()
        
        if normalized in stem_codes:
            return {
                "eligible": True,
                "cip_code": normalized,
                "title": stem_codes[normalized],
            }
        
        return {
            "eligible": False,
            "cip_code": normalized,
            "message": "CIP code not in STEM eligible list",
        }


if __name__ == "__main__":
    # Quick test
    agent = PolicyAgent()

    print("\n=== Ambiguous Query Test ===")
    queries = [
        "How long can I be unemployed on OPT?",
        "What happens if I lose my job on STEM OPT?",
        "unemployment days F1",
    ]
    import time
    for q in queries:
        response = agent.explain(q)
        print(f"\n{'='*60}")
        print(f"Query: {q}")
        print(f"{'='*60}")
        print(f"{response.answer}")
        time.sleep(60)


    print("\n=== Conflicting Authority Test ===")
    query = "Does Columbia allow more unemployment days than USCIS?"
    time.sleep(60)
    response = agent.explain(query)
    print(f"Answer: {response.answer}")
    print(f"Confidence: {response.confidence:.2f}")
    print("Citations:")
    for c in response.citations:
        print(f"  - {c}")

    print("\n=== STEM Boundary Test ===")
    cip_codes = [
        "11.0101",  # Computer Science
        "14.0901",  # Computer Engineering
        "30.3001",  # Computational Science (often borderline)
        "52.1301",  # Management Science
        "24.0102",  # General Studies (non-STEM)
    ]

    for cip in cip_codes:
        result = agent.check_stem_eligible(cip)
        print(f"CIP {cip}: {result}")

    print("\n=== Retrieval Consistency Test ===")
    search_results = agent.search("STEM OPT unemployment limit")
    time.sleep(60)
    explanation = agent.explain("What is the unemployment limit for STEM OPT?")

    print("Top Search Result:")
    print(f"  Citation: {search_results[0].citation}")
    print(f"  Text: {search_results[0].text[:120]}...")

    print("\nExplanation Citations:")
    for c in explanation.citations:
        print(f"  - {c}")

