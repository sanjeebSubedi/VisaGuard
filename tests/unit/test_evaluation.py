"""
Tests for DeepEval Evaluation Pipeline
"""

import pytest


class TestGoldenDataset:
    """Tests for the golden dataset."""

    def test_golden_dataset_exists(self):
        """Golden dataset should contain test cases."""
        from app.evaluation.deepeval_pipeline import GOLDEN_DATASET
        
        assert len(GOLDEN_DATASET) >= 10
        assert all("id" in case for case in GOLDEN_DATASET)
        assert all("input" in case for case in GOLDEN_DATASET)
        assert all("expected_output" in case for case in GOLDEN_DATASET)

    def test_golden_dataset_categories(self):
        """Golden dataset should cover key categories."""
        from app.evaluation.deepeval_pipeline import GOLDEN_DATASET
        
        categories = {case["category"] for case in GOLDEN_DATASET}
        
        assert "unemployment" in categories
        assert "employment" in categories
        assert "reporting" in categories
        assert "status" in categories


class TestVisaGuardEvaluator:
    """Tests for the evaluator."""

    def test_evaluator_initialization(self):
        """Evaluator should initialize correctly."""
        from app.evaluation.deepeval_pipeline import VisaGuardEvaluator
        
        evaluator = VisaGuardEvaluator()
        
        assert evaluator.threshold == 0.7
        assert len(evaluator.golden_dataset) >= 10

    def test_evaluate_single_mock(self):
        """Should evaluate a single test case (mock mode)."""
        from app.evaluation.deepeval_pipeline import VisaGuardEvaluator
        
        evaluator = VisaGuardEvaluator()
        
        test_data = {
            "id": "test_1",
            "input": "How many days of unemployment?",
            "expected_output": "90 days",
            "context": ["You can have up to 90 days of unemployment."],
            "category": "unemployment",
        }
        
        result = evaluator.evaluate_single(
            test_id="test_1",
            test_data=test_data,
            actual_output="You can have up to 90 days of unemployment on OPT."
        )
        
        assert result.test_id == "test_1"
        assert result.score >= 0
        assert result.score <= 1

    def test_evaluate_agent_mock(self):
        """Should run full evaluation on mock agent."""
        from app.evaluation.deepeval_pipeline import VisaGuardEvaluator
        
        evaluator = VisaGuardEvaluator()
        
        # Mock agent that always returns the expected output
        def mock_agent(question: str) -> str:
            # Find matching test case
            for case in evaluator.golden_dataset:
                if case["input"] == question:
                    return f"According to regulations, {case['expected_output']}."
            return "I don't know."
        
        report = evaluator.evaluate_agent(mock_agent)
        
        assert report.total_tests == len(evaluator.golden_dataset)
        assert report.overall_score >= 0

    def test_category_scores(self):
        """Should calculate category scores correctly."""
        from app.evaluation.deepeval_pipeline import VisaGuardEvaluator
        
        evaluator = VisaGuardEvaluator()
        
        def mock_agent(question: str) -> str:
            return "90 days unemployment 150 total 20 hours minimum"
        
        report = evaluator.evaluate_agent(mock_agent)
        
        assert "unemployment" in report.category_scores
        assert isinstance(report.category_scores["unemployment"], float)


class TestEvaluationReport:
    """Tests for evaluation reports."""

    def test_save_report(self, tmp_path):
        """Should save report to JSON."""
        from app.evaluation.deepeval_pipeline import (
            VisaGuardEvaluator,
            EvaluationReport,
            EvaluationResult,
        )
        
        evaluator = VisaGuardEvaluator()
        
        report = EvaluationReport(
            total_tests=2,
            passed_tests=1,
            failed_tests=1,
            overall_score=0.75,
            results=[
                EvaluationResult(
                    test_id="test_1",
                    passed=True,
                    score=0.9,
                    metrics={"test": 0.9},
                    input_text="Question 1?",
                    actual_output="Answer 1",
                    expected_output="Expected 1",
                    feedback="Good",
                ),
            ],
            category_scores={"unemployment": 0.75},
        )
        
        output_path = tmp_path / "test_report.json"
        saved_path = evaluator.save_report(report, output_path)
        
        assert saved_path.exists()
        
        import json
        with open(saved_path) as f:
            data = json.load(f)
        
        assert data["summary"]["total_tests"] == 2
        assert data["summary"]["overall_score"] == 0.75
        assert len(data["results"]) == 1
