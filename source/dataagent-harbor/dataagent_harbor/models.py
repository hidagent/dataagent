"""Data models for DataAgent Harbor."""

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ResultStatus(Enum):
    """Status of a test execution."""
    
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    TIMEOUT = "timeout"


class Difficulty(Enum):
    """Difficulty level of a question."""
    
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


@dataclass
class Question:
    """A test question for benchmarking.
    
    Attributes:
        id: Unique identifier for the question.
        question: The question text to send to the agent.
        expected_keywords: Keywords that should appear in the response.
        expected_pattern: Regex pattern the response should match.
        category: Category of the question.
        difficulty: Difficulty level.
        timeout: Timeout in seconds for this question.
        metadata: Additional metadata.
    """
    
    id: str
    question: str
    expected_keywords: list[str] = field(default_factory=list)
    expected_pattern: str | None = None
    category: str = "general"
    difficulty: Difficulty = Difficulty.MEDIUM
    timeout: int = 300
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Question":
        """Create a Question from a dictionary."""
        difficulty = data.get("difficulty", "medium")
        if isinstance(difficulty, str):
            difficulty = Difficulty(difficulty.lower())
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            question=data["question"],
            expected_keywords=data.get("expected_keywords", []),
            expected_pattern=data.get("expected_pattern"),
            category=data.get("category", "general"),
            difficulty=difficulty,
            timeout=data.get("timeout", 300),
            metadata=data.get("metadata", {}),
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "question": self.question,
            "expected_keywords": self.expected_keywords,
            "expected_pattern": self.expected_pattern,
            "category": self.category,
            "difficulty": self.difficulty.value,
            "timeout": self.timeout,
            "metadata": self.metadata,
        }


@dataclass
class QuestionSet:
    """A set of test questions.
    
    Attributes:
        name: Name of the question set.
        description: Description of the question set.
        version: Version of the question set.
        questions: List of questions.
        metadata: Additional metadata.
    """
    
    name: str
    description: str = ""
    version: str = "1.0"
    questions: list[Question] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QuestionSet":
        """Create a QuestionSet from a dictionary."""
        questions = [
            Question.from_dict(q) for q in data.get("questions", [])
        ]
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            version=data.get("version", "1.0"),
            questions=questions,
            metadata=data.get("metadata", {}),
        )
    
    @classmethod
    def from_json_file(cls, path: str) -> "QuestionSet":
        """Load a QuestionSet from a JSON file."""
        import json
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "questions": [q.to_dict() for q in self.questions],
            "metadata": self.metadata,
        }


@dataclass
class QuestionResult:
    """Result of a single test execution.
    
    Attributes:
        question_id: ID of the question.
        status: Test status.
        response: Response from the agent.
        response_time: Response time in seconds.
        keywords_matched: Keywords that were found in the response.
        keywords_missing: Keywords that were not found.
        pattern_matched: Whether the expected pattern matched.
        error_message: Error message if failed.
        session_id: Session ID used for the test.
        started_at: When the test started.
        finished_at: When the test finished.
        trace_id: LangSmith trace ID if tracing enabled.
        metadata: Additional metadata.
    """
    
    question_id: str
    status: ResultStatus
    response: str = ""
    response_time: float = 0.0
    keywords_matched: list[str] = field(default_factory=list)
    keywords_missing: list[str] = field(default_factory=list)
    pattern_matched: bool | None = None
    error_message: str | None = None
    session_id: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    trace_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "question_id": self.question_id,
            "status": self.status.value,
            "response": self.response,
            "response_time": self.response_time,
            "keywords_matched": self.keywords_matched,
            "keywords_missing": self.keywords_missing,
            "pattern_matched": self.pattern_matched,
            "error_message": self.error_message,
            "session_id": self.session_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "trace_id": self.trace_id,
            "metadata": self.metadata,
        }


def validate_response(
    response: str,
    expected_keywords: list[str],
    expected_pattern: str | None = None,
) -> tuple[list[str], list[str], bool | None]:
    """Validate a response against expected keywords and pattern.
    
    Args:
        response: The response text to validate.
        expected_keywords: Keywords that should appear in the response.
        expected_pattern: Regex pattern the response should match.
        
    Returns:
        Tuple of (matched_keywords, missing_keywords, pattern_matched).
    """
    response_lower = response.lower()
    
    matched = []
    missing = []
    for keyword in expected_keywords:
        if keyword.lower() in response_lower:
            matched.append(keyword)
        else:
            missing.append(keyword)
    
    pattern_matched = None
    if expected_pattern:
        pattern_matched = bool(re.search(expected_pattern, response, re.IGNORECASE))
    
    return matched, missing, pattern_matched


@dataclass
class BenchmarkReport:
    """Report of a benchmark run.
    
    Attributes:
        job_id: Unique identifier for the job.
        dataset_name: Name of the dataset used.
        server_url: URL of the server tested.
        total: Total number of tests.
        passed: Number of passed tests.
        failed: Number of failed tests.
        errors: Number of tests with errors.
        timeouts: Number of timed out tests.
        success_rate: Success rate (0.0 - 1.0).
        avg_response_time: Average response time in seconds.
        min_response_time: Minimum response time.
        max_response_time: Maximum response time.
        started_at: When the benchmark started.
        finished_at: When the benchmark finished.
        results: List of individual test results.
        metadata: Additional metadata.
    """
    
    job_id: str
    dataset_name: str
    server_url: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    timeouts: int = 0
    success_rate: float = 0.0
    avg_response_time: float = 0.0
    min_response_time: float = 0.0
    max_response_time: float = 0.0
    started_at: datetime | None = None
    finished_at: datetime | None = None
    results: list[QuestionResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def calculate_stats(self) -> None:
        """Calculate statistics from results."""
        if not self.results:
            return
        
        self.total = len(self.results)
        self.passed = sum(1 for r in self.results if r.status == ResultStatus.PASSED)
        self.failed = sum(1 for r in self.results if r.status == ResultStatus.FAILED)
        self.errors = sum(1 for r in self.results if r.status == ResultStatus.ERROR)
        self.timeouts = sum(1 for r in self.results if r.status == ResultStatus.TIMEOUT)
        
        if self.total > 0:
            self.success_rate = self.passed / self.total
        
        response_times = [r.response_time for r in self.results if r.response_time > 0]
        if response_times:
            self.avg_response_time = sum(response_times) / len(response_times)
            self.min_response_time = min(response_times)
            self.max_response_time = max(response_times)
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "job_id": self.job_id,
            "dataset_name": self.dataset_name,
            "server_url": self.server_url,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "timeouts": self.timeouts,
            "success_rate": self.success_rate,
            "avg_response_time": self.avg_response_time,
            "min_response_time": self.min_response_time,
            "max_response_time": self.max_response_time,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "results": [r.to_dict() for r in self.results],
            "metadata": self.metadata,
        }
    
    def to_markdown(self) -> str:
        """Generate a Markdown report."""
        lines = [
            f"# DataAgent Harbor Report",
            f"",
            f"## Summary",
            f"",
            f"- **Job ID**: {self.job_id}",
            f"- **Dataset**: {self.dataset_name}",
            f"- **Server**: {self.server_url}",
            f"- **Started**: {self.started_at.isoformat() if self.started_at else 'N/A'}",
            f"- **Finished**: {self.finished_at.isoformat() if self.finished_at else 'N/A'}",
            f"",
            f"## Results",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total | {self.total} |",
            f"| Passed | {self.passed} ({self.success_rate*100:.1f}%) |",
            f"| Failed | {self.failed} |",
            f"| Errors | {self.errors} |",
            f"| Timeouts | {self.timeouts} |",
            f"| Avg Response Time | {self.avg_response_time:.2f}s |",
            f"| Min Response Time | {self.min_response_time:.2f}s |",
            f"| Max Response Time | {self.max_response_time:.2f}s |",
            f"",
        ]
        
        # Add failed cases
        failed_results = [
            r for r in self.results 
            if r.status in (ResultStatus.FAILED, ResultStatus.ERROR, ResultStatus.TIMEOUT)
        ]
        
        if failed_results:
            lines.extend([
                f"## Failed Cases",
                f"",
            ])
            
            for result in failed_results:
                lines.extend([
                    f"### {result.question_id}",
                    f"",
                    f"- **Status**: {result.status.value}",
                    f"- **Response Time**: {result.response_time:.2f}s",
                ])
                
                if result.error_message:
                    lines.append(f"- **Error**: {result.error_message}")
                
                if result.keywords_missing:
                    lines.append(f"- **Missing Keywords**: {', '.join(result.keywords_missing)}")
                
                lines.append("")
        
        return "\n".join(lines)
