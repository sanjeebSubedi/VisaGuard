from app.services.dso_agent.school_resolver import SchoolResolver


def test_school_resolver_maps_known_alias_to_school_key():
    resolver = SchoolResolver({"New York University": "nyu", "NYU": "nyu"})
    assert resolver.resolve("NYU") == "nyu"


def test_school_resolver_returns_none_for_unknown_school():
    resolver = SchoolResolver({"New York University": "nyu"})
    assert resolver.resolve("Unknown School") is None
