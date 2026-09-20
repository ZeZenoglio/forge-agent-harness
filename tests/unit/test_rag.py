import pytest

from backend.agent.policies import PolicyEngine

def test_citation_validation_success():
    engine = PolicyEngine(workspace_root="/tmp")
    context = ["This is a test document containing important information.", "Another document."]
    response = 'The document states that "important information" is present.'
    
    assert engine.validate_citations(response, context) is True

def test_citation_validation_failure():
    engine = PolicyEngine(workspace_root="/tmp")
    context = ["This is a test document containing important information."]
    response = 'The document states that "completely hallucinated facts are" true.'
    
    with pytest.raises(ValueError, match="Hallucinated citation detected"):
        engine.validate_citations(response, context)

def test_citation_validation_ignores_short_quotes():
    engine = PolicyEngine(workspace_root="/tmp")
    context = ["The sky is blue."]
    # "is" is only 1 word, less than 4 words, should be ignored
    response = 'The color "is blue" but I also say "short".'
    
    assert engine.validate_citations(response, context) is True

def test_citation_validation_normalization():
    engine = PolicyEngine(workspace_root="/tmp")
    context = ["This document   has\tweird spacing."]
    response = 'Quote: "document has weird spacing."'
    
    assert engine.validate_citations(response, context) is True
