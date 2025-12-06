"""Tests for DataAgent Harbor models."""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from dataagent_harbor.models import (
    BenchmarkReport,
    Difficulty,
    Question,
    QuestionSet,
    QuestionResult,
    ResultStatus,
    validate_response,
)


class TestQuestion:
    """Tests for Question model."""
    
    def test_create_question(self):
        """Test creating a question."""
        q = Question(
            id="q1",
            question="What is Python?",
            expected_keywords=["programming", "language"],
            category="general",
        )
        
        assert q.id == "q1"
        assert q.question == "What is Python?"
        assert q.expected_keywords == ["programming", "language"]
        assert q.category == "general"
        assert q.difficulty == Difficulty.MEDIUM
    
    def test_question_from_dict(self):
        """Test creating question from dictionary."""
        data = {
            "id": "q1",
            "question": "What is Python?",
            "expected_keywords": ["programming"],
            "difficulty": "easy",
        }
        
        q = Question.from_dict(data)
        
        assert q.id == "q1"
        assert q.difficulty == Difficulty.EASY
    
    def test_question_to_dict(self):
        """Test serializing question to dictionary."""
        q = Question(
            id="q1",
            question="What is Python?",
            expected_keywords=["programming"],
        )
        
        data = q.to_dict()
        
        assert data["id"] == "q1"
        assert data["question"] == "What is Python?"
        assert data["expected_keywords"] == ["programming"]


class TestQuestionSet:
    """Tests for QuestionSet model."""
    
    def test_create_question_set(self):
        """Test creating a question set."""
        qs = QuestionSet(
            name="test-set",
            description="Test questions",
            questions=[
                Question(id="q1", question="Q1"),
                Question(id="q2", question="Q2"),
            ],
        )
        
        assert qs.name == "test-set"
        assert len(qs.questions) == 2
    
    def test_question_set_from_dict(self):
        """Test creating question set from dictionary."""
        data = {
            "name": "test-set",
            "questions": [
                {"id": "q1", "question": "Q1"},
                {"id": "q2", "question": "Q2"},
            ],
        }
        
        qs = QuestionSet.from_dict(data)
        
        assert qs.name == "test-set"
        assert len(qs.questions) == 2


class TestValidateResponse:
    """Tests for response validation."""
    
    def test_all_keywords_matched(self):
        """Test when all keywords are matched."""
        matched, missing, _ = validate_response(
            "Python is a programming language",
            ["programming", "language"],
        )
        
        assert matched == ["programming", "language"]
        assert missing == []
    
    def test_some_keywords_missing(self):
        """Test when some keywords are missing."""
        matched, missing, _ = validate_response(
            "Python is a language",
            ["programming", "language"],
        )
        
        assert matched == ["language"]
        assert missing == ["programming"]
    
    def test_case_insensitive(self):
        """Test case-insensitive matching."""
        matched, missing, _ = validate_response(
            "PYTHON is a PROGRAMMING language",
            ["python", "programming"],
        )
        
        assert matched == ["python", "programming"]
        assert missing == []
    
    def test_pattern_matched(self):
        """Test pattern matching."""
        _, _, pattern_matched = validate_response(
            "The answer is 42",
            [],
            expected_pattern=r"\d+",
        )
        
        assert pattern_matched is True
    
    def test_pattern_not_matched(self):
        """Test pattern not matching."""
        _, _, pattern_matched = validate_response(
            "The answer is unknown",
            [],
            expected_pattern=r"\d+",
        )
        
        assert pattern_matched is False


class TestQuestionResult:
    """Tests for QuestionResult model."""
    
    def test_create_result(self):
        """Test creating a test result."""
        result = QuestionResult(
            question_id="q1",
            status=ResultStatus.PASSED,
            response="Python is a programming language",
            response_time=1.5,
        )
        
        assert result.question_id == "q1"
        assert result.status == ResultStatus.PASSED
        assert result.response_time == 1.5
    
    def test_result_to_dict(self):
        """Test serializing result to dictionary."""
        result = QuestionResult(
            question_id="q1",
            status=ResultStatus.PASSED,
            response_time=1.5,
        )
        
        data = result.to_dict()
        
        assert data["question_id"] == "q1"
        assert data["status"] == "passed"
        assert data["response_time"] == 1.5


class TestBenchmarkReport:
    """Tests for BenchmarkReport model."""
    
    def test_calculate_stats(self):
        """Test calculating statistics."""
        report = BenchmarkReport(
            job_id="test-job",
            dataset_name="test-dataset",
            server_url="http://localhost:8000",
            results=[
                QuestionResult(question_id="q1", status=ResultStatus.PASSED, response_time=1.0),
                QuestionResult(question_id="q2", status=ResultStatus.PASSED, response_time=2.0),
                QuestionResult(question_id="q3", status=ResultStatus.FAILED, response_time=1.5),
                QuestionResult(question_id="q4", status=ResultStatus.ERROR, response_time=0.5),
            ],
        )
        
        report.calculate_stats()
        
        assert report.total == 4
        assert report.passed == 2
        assert report.failed == 1
        assert report.errors == 1
        assert report.success_rate == 0.5
        assert report.avg_response_time == 1.25
        assert report.min_response_time == 0.5
        assert report.max_response_time == 2.0
    
    def test_to_markdown(self):
        """Test generating markdown report."""
        report = BenchmarkReport(
            job_id="test-job",
            dataset_name="test-dataset",
            server_url="http://localhost:8000",
            total=10,
            passed=8,
            failed=2,
            success_rate=0.8,
        )
        
        md = report.to_markdown()
        
        assert "# DataAgent Harbor Report" in md
        assert "test-job" in md
        assert "test-dataset" in md


class TestValidateResponseProperties:
    """Property-based tests for response validation."""
    
    @settings(max_examples=100)
    @given(
        response=st.text(min_size=1),
        keywords=st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=5),
    )
    def test_matched_plus_missing_equals_total(self, response: str, keywords: list[str]):
        """Test that matched + missing equals total keywords."""
        matched, missing, _ = validate_response(response, keywords)
        
        assert len(matched) + len(missing) == len(keywords)
    
    @settings(max_examples=100)
    @given(
        keyword=st.text(min_size=1, max_size=20).filter(lambda x: x.strip()),
    )
    def test_keyword_in_response_is_matched(self, keyword: str):
        """Test that keyword in response is always matched."""
        response = f"This contains {keyword} in it"
        matched, missing, _ = validate_response(response, [keyword])
        
        assert keyword in matched
        assert keyword not in missing
