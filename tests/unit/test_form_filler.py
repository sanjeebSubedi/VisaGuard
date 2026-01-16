"""
Tests for Form Filler Service and DSO Agent
"""

import pytest
from pathlib import Path
import json


class TestFormFiller:
    """Tests for the FormFiller service."""

    @pytest.fixture
    def temp_templates(self, tmp_path):
        """Create temporary template directory with mappings."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        
        # Create a simple field mappings file
        mappings = {
            "Student_Name": "student_name_field",
            "Employer_Name": "employer_name_field",
            "SEVIS_ID": "sevis_id_field",
        }
        
        mappings_path = template_dir / "field_mappings.json"
        with open(mappings_path, "w") as f:
            json.dump(mappings, f)
        
        return template_dir, mappings_path

    def test_load_mappings(self, temp_templates):
        """Should load field mappings from JSON."""
        from app.services.form_filler import FormFiller
        
        template_dir, mappings_path = temp_templates
        
        filler = FormFiller(
            template_dir=template_dir,
            mappings_path=mappings_path,
        )
        
        assert "Student_Name" in filler.field_mappings
        assert filler.field_mappings["Student_Name"] == "student_name_field"

    def test_get_pdf_field_name(self, temp_templates):
        """Should return PDF field name for semantic key."""
        from app.services.form_filler import FormFiller
        
        template_dir, mappings_path = temp_templates
        filler = FormFiller(template_dir=template_dir, mappings_path=mappings_path)
        
        assert filler.get_pdf_field_name("Student_Name") == "student_name_field"
        assert filler.get_pdf_field_name("NonExistent") is None

    def test_prepare_i983_data(self):
        """Should prepare data for I-983 form."""
        from app.services.form_filler import FormFiller
        
        # Use actual mappings if available, otherwise mock
        try:
            filler = FormFiller()
        except FileNotFoundError:
            pytest.skip("Field mappings not found - run inspect_pdf_fields.py first")
        
        student_data = {
            "first_name": "John",
            "last_name": "Doe",
            "sevis_id": "N0012345678",
            "email": "john.doe@example.com",
            "school_name": "Test University",
            "degree_level": "Master's",
            "graduation_date": "05-15-2024",
            "major_cip": "11.0701 - Computer Science",
        }
        
        employer_data = {
            "company_name": "Tech Corp",
            "street": "123 Main St",
            "city": "San Francisco",
            "state": "CA",
            "zip": "94105",
            "ein": "12-3456789",
        }
        
        training_plan = {
            "start_date": "06-01-2024",
            "hours_per_week": "40",
            "salary": "$80,000/year",
            "goals": "Learn advanced software development techniques.",
            "role_description": "Software Engineer focusing on ML systems.",
        }
        
        data = filler.prepare_i983_data(student_data, employer_data, training_plan)
        
        assert "Doe, John" in data.get("Student_Name_(Surname,_Given_Name)", "")
        assert data.get("Employer_Name") == "Tech Corp"


class TestDSOAgent:
    """Tests for the DSO Agent."""

    def test_validate_data_complete(self):
        """Should validate complete data as valid."""
        from app.graph.nodes.dso_agent import DSOAgent
        
        agent = DSOAgent()
        
        student_data = {
            "first_name": "John",
            "last_name": "Doe",
            "sevis_id": "N0012345678",
            "email": "john@example.com",
            "school_name": "University",
            "degree_level": "MS",
            "graduation_date": "05-2024",
            "major_cip": "11.0701",
        }
        
        employer_data = {
            "company_name": "Tech Corp",
            "street": "123 Main",
            "city": "SF",
            "state": "CA",
            "zip": "94105",
            "ein": "12-3456789",
        }
        
        training_plan = {
            "start_date": "06-2024",
            "hours_per_week": "40",
            "salary": "$80k",
            "goals": "Learn ML",
            "role_description": "Engineer",
            "oversight": "Weekly meetings",
            "supervisor_name": "Jane Manager",
            "supervisor_email": "jane@corp.com",
        }
        
        is_valid, missing = agent.validate_data(student_data, employer_data, training_plan)
        
        assert is_valid is True
        assert len(missing) == 0

    def test_validate_data_incomplete(self):
        """Should identify missing fields."""
        from app.graph.nodes.dso_agent import DSOAgent
        
        agent = DSOAgent()
        
        student_data = {"first_name": "John"}  # Missing most fields
        employer_data = {}
        training_plan = {}
        
        is_valid, missing = agent.validate_data(student_data, employer_data, training_plan)
        
        assert is_valid is False
        assert len(missing) > 0
        assert any("last_name" in field for field in missing)
        assert any("Employer" in field for field in missing)

    def test_generate_warnings(self):
        """Should generate appropriate warnings."""
        from app.graph.nodes.dso_agent import DSOAgent
        
        agent = DSOAgent()
        
        student_data = {}
        employer_data = {}  # No E-Verify
        training_plan = {
            "hours_per_week": "15",  # Below 20
            "goals": "Short",  # Too short
            "role_description": "X",  # Too short
        }
        
        warnings = agent.generate_warnings(student_data, employer_data, training_plan)
        
        assert len(warnings) >= 2  # At least hours and E-Verify warnings
        assert any("20 hours" in w for w in warnings)
        assert any("E-Verify" in w for w in warnings)

    def test_create_preview(self):
        """Should create a form preview."""
        from app.graph.nodes.dso_agent import DSOAgent
        
        agent = DSOAgent()
        
        student_data = {
            "first_name": "John",
            "last_name": "Doe",
            "sevis_id": "N0012345678",
            "school_name": "Test University",
        }
        
        employer_data = {
            "company_name": "Tech Corp",
            "city": "SF",
            "state": "CA",
        }
        
        training_plan = {
            "start_date": "06-01-2024",
            "hours_per_week": "40",
        }
        
        preview = agent.create_preview(student_data, employer_data, training_plan)
        
        assert preview.form_type == "I-983 Training Plan"
        assert "John Doe" in preview.student_summary
        assert "Tech Corp" in preview.employer_summary
        assert preview.is_complete is False  # Missing some required fields


class TestDSOAgentNode:
    """Tests for the DSO Agent LangGraph node."""

    def test_node_creates_preview_on_first_entry(self):
        """Node should create preview and request approval on first entry."""
        from app.graph.nodes.dso_agent import dso_agent_node
        from app.graph.state import WorkflowStage
        
        state = {
            "student_data": {"first_name": "Test", "last_name": "User"},
            "employer_data": {"company_name": "TestCo"},
            "training_plan": {},
            "messages": [],
            "awaiting_human_approval": False,
        }
        
        result = dso_agent_node(state)
        
        assert result["stage"] == WorkflowStage.FORM_GENERATION
        assert result["awaiting_human_approval"] is True
        assert result["human_approval_type"] == "form_generation"
        assert len(result["messages"]) > 0
        assert "Form Preview" in result["messages"][-1]["content"]
