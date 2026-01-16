"""
Tests for Policy Agent (RAG for Regulatory Queries)
"""

import pytest
from pathlib import Path
import tempfile


class TestPolicyAgent:
    """Tests for the Policy Agent RAG system."""

    @pytest.fixture
    def temp_db_dir(self, tmp_path):
        """Create a temporary directory for ChromaDB."""
        return str(tmp_path / "chromadb")

    def test_agent_initialization(self, temp_db_dir):
        """Agent should initialize ChromaDB collection."""
        from app.graph.nodes.policy_agent import PolicyAgent
        
        agent = PolicyAgent(persist_directory=temp_db_dir)
        agent.initialize()
        
        stats = agent.get_collection_stats()
        assert stats["name"] == "regulations"
        assert stats["count"] == 0

    def test_add_document(self, temp_db_dir):
        """Should be able to add documents to the collection."""
        from app.graph.nodes.policy_agent import PolicyAgent
        
        agent = PolicyAgent(persist_directory=temp_db_dir)
        agent.initialize()
        
        doc_id = agent.add_document(
            text="During the 24-month STEM OPT extension, students must work at least 20 hours per week.",
            source="8 CFR 214.2(f)(10)(ii)(C)",
            section="STEM OPT Employment Requirements",
        )
        
        assert doc_id is not None
        assert agent.get_collection_stats()["count"] == 1

    def test_query_returns_results(self, temp_db_dir):
        """Query should return relevant results with citations."""
        from app.graph.nodes.policy_agent import PolicyAgent
        
        agent = PolicyAgent(persist_directory=temp_db_dir)
        agent.initialize()
        
        # Add some test documents
        agent.add_document(
            text="F-1 students on post-completion OPT may accumulate up to 90 days of unemployment.",
            source="8 CFR 214.2(f)(10)(ii)(E)",
            section="Unemployment Limits",
        )
        agent.add_document(
            text="STEM OPT students may accumulate up to 150 days of unemployment total.",
            source="8 CFR 214.2(f)(10)(ii)(E)",
            section="STEM OPT Unemployment",
        )
        
        result = agent.query("How many days of unemployment are allowed on OPT?")
        
        assert result.query == "How many days of unemployment are allowed on OPT?"
        assert len(result.citations) > 0
        assert result.confidence > 0

    def test_empty_query_returns_no_results(self, temp_db_dir):
        """Empty collection should return no results."""
        from app.graph.nodes.policy_agent import PolicyAgent
        
        agent = PolicyAgent(persist_directory=temp_db_dir)
        agent.initialize()
        
        result = agent.query("What are the OPT requirements?")
        
        assert result.confidence == 0.0
        assert result.needs_manual_review is True
        assert "No relevant policy information found" in result.answer

    def test_low_confidence_triggers_manual_review(self, temp_db_dir):
        """Low confidence results should flag for manual review."""
        from app.graph.nodes.policy_agent import PolicyAgent
        
        agent = PolicyAgent(persist_directory=temp_db_dir)
        agent.initialize()
        
        # Add an unrelated document
        agent.add_document(
            text="The university library is open from 8am to 10pm on weekdays.",
            source="University Handbook",
            section="Library Hours",
        )
        
        # Query about something unrelated to the document
        result = agent.query("Can I work at a coffee shop on STEM OPT?")
        
        # The confidence should be low since the document is unrelated
        # (though this depends on the embedding model)
        assert result.needs_manual_review is True or result.confidence < 0.9

    def test_batch_add_documents(self, temp_db_dir):
        """Should be able to add multiple documents in batch."""
        from app.graph.nodes.policy_agent import PolicyAgent, PolicyChunk
        
        agent = PolicyAgent(persist_directory=temp_db_dir)
        agent.initialize()
        
        docs = [
            PolicyChunk(
                id="doc1",
                text="Unpaid employment is permitted during OPT if properly documented.",
                source="USCIS Policy Manual",
                section="Unpaid Employment",
                metadata={}
            ),
            PolicyChunk(
                id="doc2",
                text="Self-employment is permitted on post-completion OPT but not on STEM extension.",
                source="8 CFR 214.2(f)",
                section="Self-Employment",
                metadata={}
            ),
        ]
        
        ids = agent.add_documents_batch(docs)
        
        assert len(ids) == 2
        assert agent.get_collection_stats()["count"] == 2
