"""Benchmark runner for DataAgent Harbor."""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.progress import Progress, TaskID
from rich.table import Table

from dataagent_harbor.client import DataAgentClient, timed_chat
from dataagent_harbor.models import (
    BenchmarkReport,
    Question,
    QuestionSet,
    QuestionResult,
    ResultStatus,
    validate_response,
)
from dataagent_harbor.tracing import TracingManager, create_example_id_from_question

logger = logging.getLogger(__name__)
console = Console()


class BenchmarkRunner:
    """Runner for executing benchmarks against DataAgent Server.
    
    Args:
        server_url: URL of the DataAgent Server.
        api_key: API key for authentication.
        timeout: Request timeout in seconds.
        concurrency: Number of concurrent requests.
        jobs_dir: Directory to store job results.
        use_websocket: Whether to use WebSocket instead of REST.
        enable_tracing: Whether to enable LangSmith tracing.
    """
    
    def __init__(
        self,
        server_url: str = "http://localhost:8000",
        api_key: str | None = None,
        timeout: float = 300.0,
        concurrency: int = 1,
        jobs_dir: str = "jobs",
        use_websocket: bool = False,
        enable_tracing: bool = False,
    ) -> None:
        self.server_url = server_url
        self.api_key = api_key
        self.timeout = timeout
        self.concurrency = concurrency
        self.jobs_dir = Path(jobs_dir)
        self.use_websocket = use_websocket
        self.enable_tracing = enable_tracing
        
        self._client: DataAgentClient | None = None
        self._tracing: TracingManager | None = None
        self._semaphore: asyncio.Semaphore | None = None
    
    @property
    def client(self) -> DataAgentClient:
        """Get or create the DataAgent client."""
        if self._client is None:
            self._client = DataAgentClient(
                base_url=self.server_url,
                api_key=self.api_key,
                timeout=self.timeout,
            )
        return self._client
    
    @property
    def tracing(self) -> TracingManager:
        """Get or create the tracing manager."""
        if self._tracing is None:
            self._tracing = TracingManager()
        return self._tracing
    
    async def check_server(self) -> bool:
        """Check if the server is healthy.
        
        Returns:
            True if server is healthy, False otherwise.
        """
        try:
            health = await self.client.health_check()
            console.print(f"[green]Server healthy: {health.get('status', 'unknown')}[/green]")
            return health.get("status") == "healthy"
        except Exception as e:
            console.print(f"[red]Server health check failed: {e}[/red]")
            return False
    
    async def run_single_test(
        self,
        question: Question,
        progress: Progress | None = None,
        task_id: TaskID | None = None,
    ) -> QuestionResult:
        """Run a single test question.
        
        Args:
            question: The question to test.
            progress: Optional progress bar.
            task_id: Optional task ID for progress.
            
        Returns:
            QuestionResult with the outcome.
        """
        result = QuestionResult(
            question_id=question.id,
            status=ResultStatus.PENDING,
            started_at=datetime.now(),
        )
        
        session_id = str(uuid.uuid4())
        result.session_id = session_id
        
        try:
            # Execute the chat request
            response = await asyncio.wait_for(
                timed_chat(
                    self.client,
                    question.question,
                    session_id=session_id,
                    use_websocket=self.use_websocket,
                ),
                timeout=question.timeout,
            )
            
            result.response = response.data.get("text", "")
            result.response_time = response.response_time
            result.finished_at = datetime.now()
            
            # Validate response
            matched, missing, pattern_matched = validate_response(
                result.response,
                question.expected_keywords,
                question.expected_pattern,
            )
            
            result.keywords_matched = matched
            result.keywords_missing = missing
            result.pattern_matched = pattern_matched
            
            # Determine status
            keywords_ok = len(missing) == 0 or len(question.expected_keywords) == 0
            pattern_ok = pattern_matched is None or pattern_matched
            
            if keywords_ok and pattern_ok:
                result.status = ResultStatus.PASSED
            else:
                result.status = ResultStatus.FAILED
                if missing:
                    result.error_message = f"Missing keywords: {', '.join(missing)}"
                elif not pattern_ok:
                    result.error_message = "Response did not match expected pattern"
        
        except asyncio.TimeoutError:
            result.status = ResultStatus.TIMEOUT
            result.error_message = f"Request timed out after {question.timeout}s"
            result.finished_at = datetime.now()
        
        except Exception as e:
            result.status = ResultStatus.ERROR
            result.error_message = str(e)
            result.finished_at = datetime.now()
            logger.exception(f"Error testing question {question.id}")
        
        if progress and task_id is not None:
            progress.advance(task_id)
        
        return result
    
    async def run_concurrent_tests(
        self,
        questions: list[Question],
        progress: Progress | None = None,
        task_id: TaskID | None = None,
    ) -> list[QuestionResult]:
        """Run multiple tests concurrently.
        
        Args:
            questions: List of questions to test.
            progress: Optional progress bar.
            task_id: Optional task ID for progress.
            
        Returns:
            List of QuestionResults.
        """
        semaphore = asyncio.Semaphore(self.concurrency)
        
        async def run_with_semaphore(question: Question) -> QuestionResult:
            async with semaphore:
                return await self.run_single_test(question, progress, task_id)
        
        tasks = [run_with_semaphore(q) for q in questions]
        return await asyncio.gather(*tasks)
    
    async def run_benchmark(
        self,
        question_set: QuestionSet,
        limit: int | None = None,
    ) -> BenchmarkReport:
        """Run a full benchmark.
        
        Args:
            question_set: The question set to run.
            limit: Optional limit on number of questions.
            
        Returns:
            BenchmarkReport with results.
        """
        # Create job directory
        job_id = datetime.now().strftime("%Y-%m-%d__%H-%M-%S")
        job_dir = self.jobs_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize report
        report = BenchmarkReport(
            job_id=job_id,
            dataset_name=question_set.name,
            server_url=self.server_url,
            started_at=datetime.now(),
            metadata={
                "concurrency": self.concurrency,
                "timeout": self.timeout,
                "use_websocket": self.use_websocket,
                "tracing_enabled": self.enable_tracing and self.tracing.enabled,
            },
        )
        
        # Check server health
        console.print("\n[bold]Checking server health...[/bold]")
        if not await self.check_server():
            console.print("[red]Server is not healthy. Aborting.[/red]")
            report.finished_at = datetime.now()
            return report
        
        # Get questions to run
        questions = question_set.questions
        if limit:
            questions = questions[:limit]
        
        console.print(f"\n[bold]Running {len(questions)} tests with concurrency {self.concurrency}...[/bold]\n")
        
        # Run tests with progress bar
        with Progress() as progress:
            task_id = progress.add_task(
                "[cyan]Testing...",
                total=len(questions),
            )
            
            results = await self.run_concurrent_tests(questions, progress, task_id)
        
        report.results = results
        report.finished_at = datetime.now()
        report.calculate_stats()
        
        # Save results
        self._save_report(report, job_dir)
        
        # Print summary
        self._print_summary(report)
        
        return report
    
    def _save_report(self, report: BenchmarkReport, job_dir: Path) -> None:
        """Save report to job directory."""
        # Save JSON report
        json_path = job_dir / "report.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
        
        # Save Markdown report
        md_path = job_dir / "report.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(report.to_markdown())
        
        console.print(f"\n[green]Results saved to {job_dir}[/green]")
    
    def _print_summary(self, report: BenchmarkReport) -> None:
        """Print summary table."""
        table = Table(title="Benchmark Results")
        
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total", str(report.total))
        table.add_row("Passed", f"{report.passed} ({report.success_rate*100:.1f}%)")
        table.add_row("Failed", str(report.failed))
        table.add_row("Errors", str(report.errors))
        table.add_row("Timeouts", str(report.timeouts))
        table.add_row("Avg Response Time", f"{report.avg_response_time:.2f}s")
        table.add_row("Min Response Time", f"{report.min_response_time:.2f}s")
        table.add_row("Max Response Time", f"{report.max_response_time:.2f}s")
        
        console.print()
        console.print(table)
    
    async def close(self) -> None:
        """Close the client."""
        if self._client:
            await self._client.close()


async def run_benchmark_from_file(
    dataset_path: str,
    server_url: str = "http://localhost:8000",
    api_key: str | None = None,
    concurrency: int = 1,
    limit: int | None = None,
    jobs_dir: str = "jobs",
    use_websocket: bool = False,
    enable_tracing: bool = False,
) -> BenchmarkReport:
    """Run a benchmark from a dataset file.
    
    Args:
        dataset_path: Path to the dataset JSON file.
        server_url: URL of the DataAgent Server.
        api_key: API key for authentication.
        concurrency: Number of concurrent requests.
        limit: Optional limit on number of questions.
        jobs_dir: Directory to store job results.
        use_websocket: Whether to use WebSocket.
        enable_tracing: Whether to enable LangSmith tracing.
        
    Returns:
        BenchmarkReport with results.
    """
    # Load dataset
    question_set = QuestionSet.from_json_file(dataset_path)
    console.print(f"[bold]Loaded dataset: {question_set.name}[/bold]")
    console.print(f"Questions: {len(question_set.questions)}")
    
    # Create runner
    runner = BenchmarkRunner(
        server_url=server_url,
        api_key=api_key,
        concurrency=concurrency,
        jobs_dir=jobs_dir,
        use_websocket=use_websocket,
        enable_tracing=enable_tracing,
    )
    
    try:
        return await runner.run_benchmark(question_set, limit=limit)
    finally:
        await runner.close()
