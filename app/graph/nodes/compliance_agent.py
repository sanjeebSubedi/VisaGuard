"""
Compliance Agent - The Reasoning Core

This agent synthesizes information from:
- Document Agent (extracted data)
- Policy Agent (regulatory rules)
- Timeline Manager (date calculations)

To produce a compliance determination with:
- A verdict (compliant, violation, warning, needs_review)
- A list of issues with severity
- Citations to specific regulations

This is the "brain" that makes the final compliance judgment.
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import OPENAI_API_KEY
from app.graph.state import VisaGuardState, ComplianceVerdict, WorkflowStage


class IssueSeverity(str, Enum):
    """Severity levels for compliance issues."""
    INFO = "info"
    WARNING = "warning"
    VIOLATION = "violation"
    CRITICAL = "critical"


@dataclass
class ComplianceIssue:
    """A single compliance issue identified by the agent."""
    issue_id: str
    severity: IssueSeverity
    category: str  # e.g., "unemployment", "job_relatedness", "hours", "reporting"
    title: str
    description: str
    regulation_citation: str
    recommendation: str


@dataclass
class ComplianceResult:
    """Complete compliance analysis result."""
    verdict: ComplianceVerdict
    summary: str
    issues: list[ComplianceIssue]
    citations: list[dict]
    confidence: float
    needs_human_review: bool
    reasoning_trace: str  # For audit logging


# Prompt for the compliance reasoning
COMPLIANCE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a compliance analyst specializing in F-1 visa regulations.
Your task is to analyze the provided data and determine if the student is in compliance with OPT regulations.

You will be provided with:
1. Student and employment data
2. Timeline calculations (unemployment days, grace period status)
3. Policy information retrieved from regulatory documents

Based on this information, you must:
1. Identify any compliance issues
2. Determine an overall verdict
3. Cite specific regulations
4. Provide recommendations

Be thorough but fair. If there are minor issues, classify them as warnings not violations.
If you are uncertain about something, flag it for human review.

IMPORTANT: Only cite regulations that were provided to you. Do not make up citations."""),
    
    ("human", """Analyze the following case for F-1 OPT compliance:

## Student Information
{student_data}

## Employment Information
{employer_data}

## Timeline Analysis
{timeline_data}

## Relevant Policy Information
{policy_data}

## Specific Question (if any)
{user_query}

Provide your analysis in the following format:

VERDICT: [COMPLIANT | WARNING | VIOLATION | NEEDS_REVIEW]

SUMMARY:
[One paragraph summary of the overall compliance status]

ISSUES:
[For each issue, provide:]
- ISSUE: [Title]
- SEVERITY: [INFO | WARNING | VIOLATION | CRITICAL]
- CATEGORY: [unemployment | job_relatedness | hours | reporting | e_verify | other]
- DESCRIPTION: [Detailed explanation]
- CITATION: [Specific regulation citation]
- RECOMMENDATION: [What the student should do]

REASONING:
[Explain your reasoning step by step]

CONFIDENCE: [0.0-1.0]
NEEDS_HUMAN_REVIEW: [YES | NO]
"""),
])


class ComplianceAgent:
    """
    Agent for analyzing F-1 OPT compliance.
    
    This agent:
    1. Receives synthesized data from other agents
    2. Uses an LLM to reason about compliance
    3. Returns a structured verdict with issues and citations
    
    Usage:
        agent = ComplianceAgent()
        result = agent.analyze(state)
    """
    
    def __init__(
        self,
        model_name: str = "gpt-4o-mini",
        temperature: float = 0.1,  # Low temperature for consistency
    ):
        """
        Initialize the Compliance Agent.
        
        Args:
            model_name: OpenAI model to use for reasoning.
            temperature: LLM temperature (lower = more deterministic).
        """
        self.model_name = model_name
        self.temperature = temperature
        self.llm: Optional[ChatOpenAI] = None
    
    def _get_llm(self) -> ChatOpenAI:
        """Get or create the LLM instance."""
        if self.llm is None:
            if not OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY not set")
            self.llm = ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                api_key=OPENAI_API_KEY,
            )
        return self.llm
    
    def analyze(
        self,
        student_data: dict,
        employer_data: dict,
        timeline_data: dict,
        policy_data: str,
        user_query: str = "",
    ) -> ComplianceResult:
        """
        Analyze compliance based on provided data.
        
        Args:
            student_data: Extracted student information.
            employer_data: Extracted employer information.
            timeline_data: Computed timeline values from TimelineManager.
            policy_data: Retrieved policy text from PolicyAgent.
            user_query: Optional specific question from the user.
            
        Returns:
            ComplianceResult with verdict, issues, and citations.
        """
        llm = self._get_llm()
        
        # Format the prompt
        chain = COMPLIANCE_PROMPT | llm
        
        response = chain.invoke({
            "student_data": self._format_dict(student_data),
            "employer_data": self._format_dict(employer_data),
            "timeline_data": self._format_dict(timeline_data),
            "policy_data": policy_data,
            "user_query": user_query or "General compliance check",
        })
        
        # Parse the response
        return self._parse_response(response.content)
    
    def _format_dict(self, data: dict) -> str:
        """Format a dictionary for inclusion in the prompt."""
        if not data:
            return "No data provided."
        
        lines = []
        for key, value in data.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)
    
    def _parse_response(self, response_text: str) -> ComplianceResult:
        """Parse the LLM response into a structured ComplianceResult."""
        lines = response_text.strip().split("\n")
        
        verdict = ComplianceVerdict.PENDING
        summary = ""
        issues = []
        reasoning = ""
        confidence = 0.5
        needs_review = True
        
        current_section = None
        current_issue = {}
        
        for line in lines:
            line = line.strip()
            
            if line.startswith("VERDICT:"):
                verdict_str = line.replace("VERDICT:", "").strip().upper()
                if "COMPLIANT" in verdict_str and "NON" not in verdict_str:
                    verdict = ComplianceVerdict.COMPLIANT
                elif "WARNING" in verdict_str:
                    verdict = ComplianceVerdict.WARNING
                elif "VIOLATION" in verdict_str:
                    verdict = ComplianceVerdict.VIOLATION
                else:
                    verdict = ComplianceVerdict.NEEDS_REVIEW
            
            elif line.startswith("SUMMARY:"):
                current_section = "summary"
            
            elif line.startswith("ISSUES:"):
                current_section = "issues"
            
            elif line.startswith("REASONING:"):
                current_section = "reasoning"
            
            elif line.startswith("CONFIDENCE:"):
                try:
                    confidence = float(line.replace("CONFIDENCE:", "").strip())
                except ValueError:
                    confidence = 0.5
            
            elif line.startswith("NEEDS_HUMAN_REVIEW:"):
                needs_review = "YES" in line.upper()
            
            elif current_section == "summary" and line:
                summary += line + " "
            
            elif current_section == "reasoning" and line:
                reasoning += line + " "
            
            elif current_section == "issues":
                if line.startswith("- ISSUE:"):
                    if current_issue.get("title"):
                        issues.append(self._create_issue(current_issue))
                    current_issue = {"title": line.replace("- ISSUE:", "").strip()}
                elif line.startswith("- SEVERITY:"):
                    current_issue["severity"] = line.replace("- SEVERITY:", "").strip()
                elif line.startswith("- CATEGORY:"):
                    current_issue["category"] = line.replace("- CATEGORY:", "").strip()
                elif line.startswith("- DESCRIPTION:"):
                    current_issue["description"] = line.replace("- DESCRIPTION:", "").strip()
                elif line.startswith("- CITATION:"):
                    current_issue["citation"] = line.replace("- CITATION:", "").strip()
                elif line.startswith("- RECOMMENDATION:"):
                    current_issue["recommendation"] = line.replace("- RECOMMENDATION:", "").strip()
        
        # Add last issue if exists
        if current_issue.get("title"):
            issues.append(self._create_issue(current_issue))
        
        # Build citations from issues
        citations = [
            {"regulation": issue.regulation_citation, "issue": issue.title}
            for issue in issues
            if issue.regulation_citation
        ]
        
        return ComplianceResult(
            verdict=verdict,
            summary=summary.strip(),
            issues=issues,
            citations=citations,
            confidence=confidence,
            needs_human_review=needs_review,
            reasoning_trace=reasoning.strip(),
        )
    
    def _create_issue(self, data: dict) -> ComplianceIssue:
        """Create a ComplianceIssue from parsed data."""
        severity_map = {
            "INFO": IssueSeverity.INFO,
            "WARNING": IssueSeverity.WARNING,
            "VIOLATION": IssueSeverity.VIOLATION,
            "CRITICAL": IssueSeverity.CRITICAL,
        }
        
        return ComplianceIssue(
            issue_id=f"issue_{hash(data.get('title', ''))}"[:16],
            severity=severity_map.get(data.get("severity", "").upper(), IssueSeverity.WARNING),
            category=data.get("category", "other").lower(),
            title=data.get("title", "Unknown Issue"),
            description=data.get("description", ""),
            regulation_citation=data.get("citation", ""),
            recommendation=data.get("recommendation", ""),
        )


def compliance_agent_node(state: VisaGuardState) -> dict:
    """
    LangGraph node wrapper for ComplianceAgent.
    
    This node:
    1. Retrieves data from state references (would fetch from DB in production)
    2. Runs the compliance analysis
    3. Updates state with results
    """
    agent = ComplianceAgent()
    
    # In production, these would be fetched from secure storage using IDs
    student_data = state.get("student_data", {})
    employer_data = state.get("employer_data", {})
    timeline_data = state.get("timeline", {})
    policy_result = state.get("policy_result", {})
    
    policy_text = policy_result.get("answer", "") if policy_result else ""
    
    # Get any user query from messages
    messages = state.get("messages", [])
    user_query = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_query = msg.get("content", "")
            break
    
    try:
        result = agent.analyze(
            student_data=student_data,
            employer_data=employer_data,
            timeline_data=timeline_data,
            policy_data=policy_text,
            user_query=user_query,
        )
        
        # Convert issues to dicts for state storage
        issues_dict = [
            {
                "issue_id": issue.issue_id,
                "severity": issue.severity.value,
                "category": issue.category,
                "title": issue.title,
                "description": issue.description,
                "citation": issue.regulation_citation,
                "recommendation": issue.recommendation,
            }
            for issue in result.issues
        ]
        
        return {
            **state,
            "stage": WorkflowStage.COMPLIANCE_REVIEW if not result.needs_human_review else WorkflowStage.HUMAN_REVIEW,
            "compliance_verdict": result.verdict,
            "compliance_issues": issues_dict,
            "compliance_citations": result.citations,
            "awaiting_human_approval": result.needs_human_review,
            "human_approval_type": "compliance_review" if result.needs_human_review else None,
        }
    
    except Exception as e:
        return {
            **state,
            "stage": WorkflowStage.ERROR,
            "error_message": f"Compliance analysis failed: {str(e)}",
        }
