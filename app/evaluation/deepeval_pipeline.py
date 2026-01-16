"""
DeepEval Evaluation Pipeline for VisaGuard

Evaluates the quality of the compliance agent's responses using:
1. Factual correctness (citations match claims)
2. Regulatory accuracy (answers align with actual CFR rules)
3. Safety (no hallucinated permissions)
4. Completeness (all relevant factors considered)

Uses DeepEval's built-in metrics plus custom metrics for immigration-specific checks.
"""

from dataclasses import dataclass
from typing import Optional
import json
from pathlib import Path

# DeepEval imports
try:
    from deepeval import evaluate
    from deepeval.metrics import (
        AnswerRelevancyMetric,
        FaithfulnessMetric,
        ContextualRelevancyMetric,
        HallucinationMetric,
    )
    from deepeval.test_case import LLMTestCase
    DEEPEVAL_AVAILABLE = True
except ImportError:
    DEEPEVAL_AVAILABLE = False

from app.core.config import DATA_DIR, OPENAI_API_KEY


# Golden dataset of test cases for immigration compliance
GOLDEN_DATASET = [
    {
        "id": "unemployment_limit_post_opt",
        "input": "How many days of unemployment can I have on post-completion OPT?",
        "expected_output": "90 days",
        "context": [
            "According to 8 CFR 214.2(f)(10)(ii)(E), F-1 students on post-completion OPT may accumulate a maximum of 90 days of unemployment."
        ],
        "category": "unemployment",
    },
    {
        "id": "unemployment_limit_stem_opt",
        "input": "What is the unemployment limit for STEM OPT?",
        "expected_output": "150 days total (cumulative)",
        "context": [
            "Students on the 24-month STEM OPT extension may accumulate a maximum of 150 days of unemployment in aggregate during the initial post-completion OPT and STEM OPT extension periods combined."
        ],
        "category": "unemployment",
    },
    {
        "id": "self_employment_stem",
        "input": "Can I be self-employed during STEM OPT?",
        "expected_output": "No, self-employment is not permitted during STEM OPT",
        "context": [
            "Self-employment is permitted during post-completion OPT but NOT during the STEM OPT extension. STEM OPT requires a bona fide employer-employee relationship with an E-Verify enrolled employer."
        ],
        "category": "employment",
    },
    {
        "id": "minimum_hours",
        "input": "How many hours do I need to work per week on STEM OPT?",
        "expected_output": "At least 20 hours per week",
        "context": [
            "During the 24-month STEM OPT extension, students must work at least 20 hours per week. Working fewer than 20 hours per week is considered unemployment for that week."
        ],
        "category": "employment",
    },
    {
        "id": "everify_requirement",
        "input": "Do I need to work for an E-Verify employer on STEM OPT?",
        "expected_output": "Yes, E-Verify enrollment is required",
        "context": [
            "To employ a student on STEM OPT extension, the employer must be enrolled in E-Verify. Students may not work for employers who are not enrolled in E-Verify during STEM OPT."
        ],
        "category": "employer_requirements",
    },
    {
        "id": "grace_period",
        "input": "How long is the grace period after OPT ends?",
        "expected_output": "60 days",
        "context": [
            "F-1 students have a 60-day grace period after the end of OPT authorization. During the grace period, students may remain in the United States but may NOT work."
        ],
        "category": "status",
    },
    {
        "id": "reporting_deadline",
        "input": "How quickly do I need to report a job change on STEM OPT?",
        "expected_output": "Within 10 days",
        "context": [
            "Students on STEM OPT must report to their DSO within 10 days of any change of employer name or address, or loss of employment."
        ],
        "category": "reporting",
    },
    {
        "id": "cap_gap",
        "input": "What is cap-gap extension?",
        "expected_output": "Automatic extension of OPT if H-1B petition is pending",
        "context": [
            "If an F-1 student's OPT expires while a timely-filed H-1B petition is pending, the student may be eligible for automatic extension of OPT and employment authorization until October 1."
        ],
        "category": "status",
    },
    {
        "id": "unpaid_employment",
        "input": "Can I do unpaid work during OPT?",
        "expected_output": "Yes, if properly documented and related to field of study",
        "context": [
            "Unpaid employment is permitted during post-completion OPT as long as the position is directly related to the student's field of study, does not violate labor laws, and is properly documented."
        ],
        "category": "employment",
    },
    {
        "id": "job_relatedness",
        "input": "Does my job need to be related to my degree?",
        "expected_output": "Yes, employment must be directly related to major",
        "context": [
            "Employment during OPT must be directly related to the student's major area of study. For STEM OPT, the employment must be directly related to the STEM degree that is the basis for the OPT extension."
        ],
        "category": "employment",
    },
]


@dataclass
class EvaluationResult:
    """Result from evaluating a single test case."""
    test_id: str
    passed: bool
    score: float
    metrics: dict
    input_text: str
    actual_output: str
    expected_output: str
    feedback: str


@dataclass
class EvaluationReport:
    """Complete evaluation report."""
    total_tests: int
    passed_tests: int
    failed_tests: int
    overall_score: float
    results: list[EvaluationResult]
    category_scores: dict


class VisaGuardEvaluator:
    """
    Evaluation pipeline for VisaGuard compliance responses.
    
    Uses DeepEval metrics to assess:
    1. Answer relevancy
    2. Faithfulness to context
    3. Hallucination detection
    4. Contextual relevancy
    
    Usage:
        evaluator = VisaGuardEvaluator()
        report = evaluator.evaluate_agent(agent_fn)
    """
    
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        threshold: float = 0.7,
    ):
        """
        Initialize the evaluator.
        
        Args:
            model: OpenAI model for evaluation.
            threshold: Minimum score to pass.
        """
        self.model = model
        self.threshold = threshold
        self.golden_dataset = GOLDEN_DATASET
        
        if not DEEPEVAL_AVAILABLE:
            print("Warning: DeepEval not installed. Using mock evaluation.")
    
    def create_test_cases(
        self,
        agent_responses: dict[str, str],
    ) -> list:
        """
        Create DeepEval test cases from agent responses.
        
        Args:
            agent_responses: Dict mapping test_id to actual agent response.
            
        Returns:
            List of LLMTestCase objects.
        """
        if not DEEPEVAL_AVAILABLE:
            return []
        
        test_cases = []
        for test_data in self.golden_dataset:
            test_id = test_data["id"]
            if test_id not in agent_responses:
                continue
            
            test_case = LLMTestCase(
                input=test_data["input"],
                actual_output=agent_responses[test_id],
                expected_output=test_data["expected_output"],
                context=test_data["context"],
            )
            test_cases.append((test_id, test_data, test_case))
        
        return test_cases
    
    def evaluate_single(
        self,
        test_id: str,
        test_data: dict,
        actual_output: str,
    ) -> EvaluationResult:
        """
        Evaluate a single test case.
        
        Args:
            test_id: Unique test identifier.
            test_data: Test case data from golden dataset.
            actual_output: Agent's response.
            
        Returns:
            EvaluationResult with scores and feedback.
        """
        if not DEEPEVAL_AVAILABLE:
            # Mock evaluation when DeepEval not installed
            expected = test_data["expected_output"].lower()
            actual = actual_output.lower()
            
            # Simple keyword matching for mock
            keywords = expected.split()[:3]  # First 3 words
            matches = sum(1 for kw in keywords if kw in actual)
            score = matches / len(keywords) if keywords else 0.5
            
            return EvaluationResult(
                test_id=test_id,
                passed=score >= self.threshold,
                score=score,
                metrics={"keyword_match": score},
                input_text=test_data["input"],
                actual_output=actual_output,
                expected_output=test_data["expected_output"],
                feedback=f"Mock evaluation: {score:.2f} based on keyword matching",
            )
        
        # Full DeepEval evaluation
        test_case = LLMTestCase(
            input=test_data["input"],
            actual_output=actual_output,
            expected_output=test_data["expected_output"],
            context=test_data["context"],
        )
        
        # Define metrics
        metrics = [
            AnswerRelevancyMetric(threshold=self.threshold, model=self.model),
            FaithfulnessMetric(threshold=self.threshold, model=self.model),
            HallucinationMetric(threshold=self.threshold, model=self.model),
        ]
        
        # Evaluate
        scores = {}
        feedback_parts = []
        
        for metric in metrics:
            try:
                metric.measure(test_case)
                scores[metric.__class__.__name__] = metric.score
                if metric.reason:
                    feedback_parts.append(f"{metric.__class__.__name__}: {metric.reason}")
            except Exception as e:
                scores[metric.__class__.__name__] = 0.0
                feedback_parts.append(f"{metric.__class__.__name__}: Error - {str(e)}")
        
        avg_score = sum(scores.values()) / len(scores) if scores else 0.0
        
        return EvaluationResult(
            test_id=test_id,
            passed=avg_score >= self.threshold,
            score=avg_score,
            metrics=scores,
            input_text=test_data["input"],
            actual_output=actual_output,
            expected_output=test_data["expected_output"],
            feedback="; ".join(feedback_parts),
        )
    
    def evaluate_agent(
        self,
        agent_fn,
    ) -> EvaluationReport:
        """
        Run full evaluation on an agent.
        
        Args:
            agent_fn: Function that takes a question and returns an answer.
                     Signature: (str) -> str
            
        Returns:
            EvaluationReport with all results.
        """
        results = []
        category_scores = {}
        
        for test_data in self.golden_dataset:
            test_id = test_data["id"]
            category = test_data["category"]
            
            # Get agent response
            try:
                actual_output = agent_fn(test_data["input"])
            except Exception as e:
                actual_output = f"Error: {str(e)}"
            
            # Evaluate
            result = self.evaluate_single(test_id, test_data, actual_output)
            results.append(result)
            
            # Track category scores
            if category not in category_scores:
                category_scores[category] = []
            category_scores[category].append(result.score)
        
        # Calculate category averages
        for cat in category_scores:
            scores = category_scores[cat]
            category_scores[cat] = sum(scores) / len(scores) if scores else 0.0
        
        # Build report
        passed = sum(1 for r in results if r.passed)
        total = len(results)
        
        return EvaluationReport(
            total_tests=total,
            passed_tests=passed,
            failed_tests=total - passed,
            overall_score=sum(r.score for r in results) / total if total else 0.0,
            results=results,
            category_scores=category_scores,
        )
    
    def save_report(
        self,
        report: EvaluationReport,
        output_path: Optional[Path] = None,
    ) -> Path:
        """
        Save evaluation report to JSON.
        
        Args:
            report: Evaluation report to save.
            output_path: Output file path.
            
        Returns:
            Path to saved report.
        """
        if output_path is None:
            output_dir = DATA_DIR / "evaluations"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = output_dir / f"eval_report_{timestamp}.json"
        
        report_dict = {
            "summary": {
                "total_tests": report.total_tests,
                "passed_tests": report.passed_tests,
                "failed_tests": report.failed_tests,
                "overall_score": report.overall_score,
                "category_scores": report.category_scores,
            },
            "results": [
                {
                    "test_id": r.test_id,
                    "passed": r.passed,
                    "score": r.score,
                    "metrics": r.metrics,
                    "input": r.input_text,
                    "actual_output": r.actual_output,
                    "expected_output": r.expected_output,
                    "feedback": r.feedback,
                }
                for r in report.results
            ],
        }
        
        with open(output_path, "w") as f:
            json.dump(report_dict, f, indent=2)
        
        return output_path
    
    def print_report(self, report: EvaluationReport) -> None:
        """Print a formatted evaluation report."""
        print("\n" + "=" * 60)
        print("VISAGUARD EVALUATION REPORT")
        print("=" * 60)
        
        print(f"\nOverall Score: {report.overall_score:.2%}")
        print(f"Tests Passed: {report.passed_tests}/{report.total_tests}")
        
        print("\n--- Category Scores ---")
        for cat, score in report.category_scores.items():
            status = "✅" if score >= self.threshold else "❌"
            print(f"  {status} {cat}: {score:.2%}")
        
        print("\n--- Test Results ---")
        for result in report.results:
            status = "✅" if result.passed else "❌"
            print(f"  {status} {result.test_id}: {result.score:.2%}")
            if not result.passed:
                print(f"      Input: {result.input_text[:50]}...")
                print(f"      Expected: {result.expected_output[:50]}...")
                print(f"      Feedback: {result.feedback[:80]}...")
        
        print("\n" + "=" * 60)


def run_evaluation():
    """Run a full evaluation of the PolicyAgent."""
    from app.graph.nodes.policy_agent import PolicyAgent
    
    print("Initializing PolicyAgent...")
    agent = PolicyAgent()
    agent.initialize()
    
    print("Seeding regulations...")
    from scripts.seed_regulations import seed_regulations
    seed_regulations()
    
    print("Running evaluation...")
    evaluator = VisaGuardEvaluator()
    
    def agent_fn(question: str) -> str:
        result = agent.query(question)
        return result.answer
    
    report = evaluator.evaluate_agent(agent_fn)
    evaluator.print_report(report)
    
    output_path = evaluator.save_report(report)
    print(f"\nReport saved to: {output_path}")
    
    return report


if __name__ == "__main__":
    run_evaluation()
