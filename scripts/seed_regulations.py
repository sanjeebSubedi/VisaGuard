"""
Sample F-1 OPT Regulations for PolicyAgent

This script seeds the PolicyAgent vector store with key regulatory excerpts.
These are paraphrased versions of actual USCIS regulations for testing.

Run with: uv run python scripts/seed_regulations.py
"""

import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.graph.nodes.policy_agent import PolicyAgent, PolicyChunk


REGULATIONS = [
    # Unemployment limits
    PolicyChunk(
        id="reg_unemployment_post_opt",
        text="""Post-Completion OPT Unemployment Limit:
F-1 students on post-completion OPT may accumulate a maximum of 90 days of unemployment. 
Unemployment is counted from the OPT start date, not the graduation date. 
Students who exceed 90 days of unemployment are in violation of their status.""",
        source="8 CFR 214.2(f)(10)(ii)(E)",
        section="Unemployment Limits - Post-Completion OPT",
        metadata={"category": "unemployment"}
    ),
    PolicyChunk(
        id="reg_unemployment_stem_opt",
        text="""STEM OPT Unemployment Limit:
Students on the 24-month STEM OPT extension may accumulate a maximum of 150 days of unemployment 
in aggregate during the initial post-completion OPT and STEM OPT extension periods combined.
This is not an additional 150 days on top of the original 90 days.""",
        source="8 CFR 214.2(f)(10)(ii)(E)",
        section="Unemployment Limits - STEM OPT",
        metadata={"category": "unemployment"}
    ),
    
    # Employment requirements
    PolicyChunk(
        id="reg_hours_stem_opt",
        text="""STEM OPT Minimum Hours Requirement:
During the 24-month STEM OPT extension, students must work at least 20 hours per week.
This applies to each employer if the student has multiple employers.
Working fewer than 20 hours per week is considered unemployment for that week.""",
        source="8 CFR 214.2(f)(10)(ii)(C)(4)",
        section="STEM OPT Employment Requirements",
        metadata={"category": "employment"}
    ),
    PolicyChunk(
        id="reg_everify",
        text="""E-Verify Requirement for STEM OPT:
To employ a student on STEM OPT extension, the employer must be enrolled in E-Verify.
The E-Verify company ID number must be listed on the Form I-983 Training Plan.
Students may not work for employers who are not enrolled in E-Verify during STEM OPT.""",
        source="8 CFR 214.2(f)(10)(ii)(C)(2)",
        section="E-Verify Requirement",
        metadata={"category": "employer_requirements"}
    ),
    
    # Job relatedness
    PolicyChunk(
        id="reg_job_relatedness",
        text="""OPT Employment Relationship to Degree:
Employment during OPT must be directly related to the student's major area of study.
For STEM OPT, the employment must be directly related to the STEM degree that is the basis
for the OPT extension. The student's role, not just the company's industry, must be STEM-related.""",
        source="8 CFR 214.2(f)(10)(ii)(A)",
        section="Job Relatedness Requirements",
        metadata={"category": "employment"}
    ),
    
    # Unpaid employment
    PolicyChunk(
        id="reg_unpaid_employment",
        text="""Unpaid Employment During OPT:
Unpaid employment is permitted during post-completion OPT as long as:
1. The position is directly related to the student's field of study
2. The employment does not violate labor laws
3. The employment is properly documented
Unpaid employment counts toward the unemployment limit if not properly documented.""",
        source="USCIS Policy Manual - OPT",
        section="Unpaid Employment",
        metadata={"category": "employment"}
    ),
    
    # Self-employment
    PolicyChunk(
        id="reg_self_employment",
        text="""Self-Employment During OPT:
Self-employment is permitted during post-completion OPT if the student:
1. Has proper business licenses
2. Is actively engaged in business related to their degree
3. Works at least 20 hours per week

IMPORTANT: Self-employment is NOT permitted during the STEM OPT extension.
STEM OPT requires a bona fide employer-employee relationship with an E-Verify employer.""",
        source="8 CFR 214.2(f)(10)(ii)(C)",
        section="Self-Employment Restrictions",
        metadata={"category": "employment"}
    ),
    
    # Reporting requirements
    PolicyChunk(
        id="reg_reporting",
        text="""STEM OPT Reporting Requirements:
Students on STEM OPT must report to their DSO within 10 days of:
1. Any change of legal name
2. Any change of residential address
3. Any change of employer name or address
4. Loss of employment
5. Any change in employer's E-Verify Company ID number

Failure to report changes may result in termination of STEM OPT authorization.""",
        source="8 CFR 214.2(f)(12)(ii)",
        section="STEM OPT Reporting Requirements",
        metadata={"category": "reporting"}
    ),
    
    # Grace period
    PolicyChunk(
        id="reg_grace_period",
        text="""60-Day Grace Period:
F-1 students have a 60-day grace period after:
1. Completion of their program of study
2. End of OPT authorization (if not extended)

During the grace period, students may:
- Remain in the United States
- Prepare for departure
- Transfer to another school
- Apply for a change of status

Students may NOT work during the grace period.""",
        source="8 CFR 214.2(f)(5)(iv)",
        section="Grace Period",
        metadata={"category": "status"}
    ),
    
    # Cap-gap extension
    PolicyChunk(
        id="reg_cap_gap",
        text="""Cap-Gap Extension:
If an F-1 student's OPT expires while a timely-filed H-1B petition is pending,
the student may be eligible for automatic extension of OPT and employment authorization
until October 1 of the fiscal year for which the H-1B is requested (cap-gap extension).

Requirements:
1. H-1B petition must be timely filed
2. H-1B must request change of status
3. Student must have valid OPT when H-1B is filed""",
        source="8 CFR 214.2(f)(5)(vi)",
        section="Cap-Gap Extension",
        metadata={"category": "status"}
    ),
]


def seed_regulations():
    """Seed the PolicyAgent with sample regulations."""
    print("Initializing PolicyAgent...")
    agent = PolicyAgent()
    agent.initialize()
    
    print(f"Current collection count: {agent.get_collection_stats()['count']}")
    
    print(f"Adding {len(REGULATIONS)} regulatory documents...")
    ids = agent.add_documents_batch(REGULATIONS)
    
    print(f"Added {len(ids)} documents")
    print(f"New collection count: {agent.get_collection_stats()['count']}")
    
    # Test a query
    print("\nTesting query: 'Can I work unpaid during OPT?'")
    result = agent.query("Can I work unpaid during OPT?")
    print(f"Confidence: {result.confidence:.3f}")
    print(f"Needs manual review: {result.needs_manual_review}")
    print(f"Answer preview: {result.answer[:200]}...")
    
    return agent


if __name__ == "__main__":
    seed_regulations()
