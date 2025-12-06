"""LangSmith tracing integration for DataAgent Harbor."""

import hashlib
import os
import uuid
from typing import Any

from langsmith import Client


def create_example_id_from_question(question: str, seed: int = 42) -> str:
    """Create a deterministic UUID from a question string.
    
    Normalizes the question by stripping whitespace and creating a
    SHA-256 hash, then converting to a UUID for LangSmith compatibility.
    
    Args:
        question: The question string to hash.
        seed: Integer seed to avoid collisions.
        
    Returns:
        A UUID string generated from the hash.
    """
    normalized = question.strip()
    seeded_data = seed.to_bytes(8, byteorder="big") + normalized.encode("utf-8")
    hash_bytes = hashlib.sha256(seeded_data).digest()
    example_uuid = uuid.UUID(bytes=hash_bytes[:16])
    return str(example_uuid)


class TracingManager:
    """Manager for LangSmith tracing integration.
    
    Handles creating datasets, experiments, and adding feedback
    to LangSmith for DataAgent Harbor benchmarks.
    """
    
    def __init__(self) -> None:
        self._client: Client | None = None
        self._enabled = self._check_enabled()
    
    def _check_enabled(self) -> bool:
        """Check if LangSmith tracing is enabled."""
        api_key = os.environ.get("LANGSMITH_API_KEY")
        tracing_v2 = os.environ.get("LANGSMITH_TRACING_V2", "").lower()
        return bool(api_key) and tracing_v2 in ("true", "1", "yes")
    
    @property
    def enabled(self) -> bool:
        """Whether tracing is enabled."""
        return self._enabled
    
    @property
    def client(self) -> Client:
        """Get LangSmith client."""
        if self._client is None:
            self._client = Client()
        return self._client
    
    @property
    def project_name(self) -> str:
        """Get the LangSmith project name."""
        return os.environ.get("LANGSMITH_PROJECT", "dataagent-harbor")
    
    @property
    def experiment_name(self) -> str | None:
        """Get the LangSmith experiment name if set."""
        return os.environ.get("LANGSMITH_EXPERIMENT") or None
    
    def create_dataset(
        self,
        name: str,
        questions: list[dict[str, Any]],
        description: str = "",
    ) -> str:
        """Create a LangSmith dataset from questions.
        
        Args:
            name: Dataset name.
            questions: List of question dictionaries.
            description: Dataset description.
            
        Returns:
            Dataset ID.
        """
        if not self.enabled:
            raise RuntimeError("LangSmith tracing is not enabled")
        
        # Create dataset
        dataset = self.client.create_dataset(
            dataset_name=name,
            description=description,
        )
        
        # Create examples
        examples = []
        for q in questions:
            example_id = create_example_id_from_question(q["question"])
            examples.append({
                "id": example_id,
                "inputs": {
                    "question_id": q.get("id", ""),
                    "question": q["question"],
                    "category": q.get("category", "general"),
                    "difficulty": q.get("difficulty", "medium"),
                },
                "outputs": {
                    "expected_keywords": q.get("expected_keywords", []),
                    "expected_pattern": q.get("expected_pattern"),
                },
            })
        
        self.client.create_examples(dataset_id=dataset.id, examples=examples)
        
        return str(dataset.id)
    
    def add_feedback(
        self,
        run_id: str,
        score: float,
        key: str = "harbor_score",
        comment: str | None = None,
    ) -> None:
        """Add feedback to a LangSmith run.
        
        Args:
            run_id: The run ID to add feedback to.
            score: Score value (0.0 - 1.0).
            key: Feedback key name.
            comment: Optional comment.
        """
        if not self.enabled:
            return
        
        self.client.create_feedback(
            run_id=run_id,
            key=key,
            score=score,
            comment=comment,
        )
    
    def add_batch_feedback(
        self,
        results: list[dict[str, Any]],
        project_name: str | None = None,
    ) -> dict[str, int]:
        """Add feedback for multiple results.
        
        Args:
            results: List of result dictionaries with question_id and status.
            project_name: LangSmith project name to search for traces.
            
        Returns:
            Dictionary with counts of success, skipped, error.
        """
        if not self.enabled:
            return {"success": 0, "skipped": len(results), "error": 0}
        
        project = project_name or self.project_name
        counts = {"success": 0, "skipped": 0, "error": 0}
        
        for result in results:
            question_id = result.get("question_id", "")
            status = result.get("status", "")
            
            # Calculate score based on status
            if status == "passed":
                score = 1.0
            elif status == "failed":
                score = 0.0
            else:
                score = 0.0
            
            try:
                # Find the trace by question_id in metadata
                runs = list(self.client.list_runs(
                    project_name=project,
                    filter=f'and(eq(metadata_key, "question_id"), eq(metadata_value, "{question_id}"))',
                    is_root=True,
                    limit=1,
                ))
                
                if not runs:
                    counts["skipped"] += 1
                    continue
                
                run = runs[0]
                self.add_feedback(
                    run_id=str(run.id),
                    score=score,
                    key="harbor_score",
                    comment=f"Status: {status}",
                )
                counts["success"] += 1
                
            except Exception as e:
                counts["error"] += 1
        
        return counts
