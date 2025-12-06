"""Test configuration and fixtures for DataAgent Harbor."""

import pytest


@pytest.fixture
def sample_questions():
    """Sample questions for testing."""
    return [
        {
            "id": "q1",
            "question": "What is Python?",
            "expected_keywords": ["programming", "language"],
            "category": "general",
            "difficulty": "easy",
        },
        {
            "id": "q2",
            "question": "How do I create a list?",
            "expected_keywords": ["list", "[]"],
            "category": "python",
            "difficulty": "easy",
        },
    ]


@pytest.fixture
def sample_question_set(sample_questions):
    """Sample question set for testing."""
    from dataagent_harbor.models import QuestionSet
    
    return QuestionSet.from_dict({
        "name": "test-set",
        "description": "Test questions",
        "questions": sample_questions,
    })
