from app.services.dso_agent.router import route_intent


def test_route_intent_identifies_general_policy_question():
    assert route_intent("Can I work two jobs on OPT?") == "general_policy"


def test_route_intent_identifies_school_procedure_question():
    assert route_intent("How do I get a travel signature?") == "school_procedure"


def test_route_intent_identifies_escalation_sensitive_question():
    assert route_intent("Am I out of status if I already exceeded my unemployment limit?") == "escalation_sensitive"
