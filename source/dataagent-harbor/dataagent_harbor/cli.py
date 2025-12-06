"""Command-line interface for DataAgent Harbor."""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console

load_dotenv()

console = Console()


def cmd_run(args: argparse.Namespace) -> int:
    """Run benchmark command."""
    from dataagent_harbor.runner import run_benchmark_from_file
    
    # Get configuration from args or environment
    server_url = args.server or os.environ.get(
        "DATAAGENT_HARBOR_SERVER", "http://localhost:8000"
    )
    api_key = args.api_key or os.environ.get("DATAAGENT_HARBOR_API_KEY")
    
    console.print(f"[bold]DataAgent Harbor Benchmark[/bold]")
    console.print(f"Server: {server_url}")
    console.print(f"Dataset: {args.dataset}")
    console.print(f"Concurrency: {args.concurrency}")
    
    if args.limit:
        console.print(f"Limit: {args.limit}")
    
    if args.trace:
        console.print("[yellow]LangSmith tracing enabled[/yellow]")
    
    # Run benchmark
    report = asyncio.run(run_benchmark_from_file(
        dataset_path=args.dataset,
        server_url=server_url,
        api_key=api_key,
        concurrency=args.concurrency,
        limit=args.limit,
        jobs_dir=args.jobs_dir,
        use_websocket=args.websocket,
        enable_tracing=args.trace,
    ))
    
    # Return exit code based on success rate
    if report.success_rate >= 0.9:
        return 0
    elif report.success_rate >= 0.5:
        return 1
    else:
        return 2


def cmd_report(args: argparse.Namespace) -> int:
    """Generate report command."""
    job_dir = Path(args.job_dir)
    
    if not job_dir.exists():
        console.print(f"[red]Job directory not found: {job_dir}[/red]")
        return 1
    
    report_json = job_dir / "report.json"
    if not report_json.exists():
        console.print(f"[red]Report not found: {report_json}[/red]")
        return 1
    
    with open(report_json, "r", encoding="utf-8") as f:
        report_data = json.load(f)
    
    if args.format == "json":
        console.print_json(data=report_data)
    elif args.format == "markdown":
        report_md = job_dir / "report.md"
        if report_md.exists():
            console.print(report_md.read_text())
        else:
            console.print("[yellow]Markdown report not found[/yellow]")
    else:
        # Summary format
        from rich.table import Table
        
        table = Table(title=f"Benchmark Report: {report_data['job_id']}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Dataset", report_data["dataset_name"])
        table.add_row("Server", report_data["server_url"])
        table.add_row("Total", str(report_data["total"]))
        table.add_row("Passed", f"{report_data['passed']} ({report_data['success_rate']*100:.1f}%)")
        table.add_row("Failed", str(report_data["failed"]))
        table.add_row("Errors", str(report_data["errors"]))
        table.add_row("Timeouts", str(report_data["timeouts"]))
        table.add_row("Avg Response Time", f"{report_data['avg_response_time']:.2f}s")
        
        console.print(table)
    
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    """Analyze results command."""
    job_dir = Path(args.job_dir)
    
    if not job_dir.exists():
        console.print(f"[red]Job directory not found: {job_dir}[/red]")
        return 1
    
    report_json = job_dir / "report.json"
    if not report_json.exists():
        console.print(f"[red]Report not found: {report_json}[/red]")
        return 1
    
    with open(report_json, "r", encoding="utf-8") as f:
        report_data = json.load(f)
    
    results = report_data.get("results", [])
    
    # Filter results
    if args.failed_only:
        results = [r for r in results if r["status"] in ("failed", "error", "timeout")]
    
    if args.category:
        # Would need to load original dataset to filter by category
        pass
    
    # Print results
    from rich.table import Table
    
    table = Table(title="Test Results Analysis")
    table.add_column("ID", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Time", style="yellow")
    table.add_column("Error", style="red")
    
    for result in results[:args.limit or 50]:
        status_style = {
            "passed": "[green]PASSED[/green]",
            "failed": "[red]FAILED[/red]",
            "error": "[red]ERROR[/red]",
            "timeout": "[yellow]TIMEOUT[/yellow]",
        }.get(result["status"], result["status"])
        
        table.add_row(
            result["question_id"],
            status_style,
            f"{result['response_time']:.2f}s",
            result.get("error_message", "")[:50] if result.get("error_message") else "",
        )
    
    console.print(table)
    
    if len(results) > (args.limit or 50):
        console.print(f"\n[dim]Showing {args.limit or 50} of {len(results)} results[/dim]")
    
    return 0


def cmd_create_dataset(args: argparse.Namespace) -> int:
    """Create a sample dataset command."""
    sample_dataset = {
        "name": args.name or "sample-dataset",
        "description": "Sample test dataset for DataAgent Harbor",
        "version": "1.0",
        "questions": [
            {
                "id": "q1",
                "question": "What is Python?",
                "expected_keywords": ["programming", "language"],
                "category": "general",
                "difficulty": "easy",
            },
            {
                "id": "q2",
                "question": "How do I create a list in Python?",
                "expected_keywords": ["list", "[]"],
                "category": "python",
                "difficulty": "easy",
            },
            {
                "id": "q3",
                "question": "Explain the difference between a list and a tuple in Python.",
                "expected_keywords": ["list", "tuple", "mutable", "immutable"],
                "category": "python",
                "difficulty": "medium",
            },
        ],
    }
    
    output_path = Path(args.output)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(sample_dataset, f, indent=2, ensure_ascii=False)
    
    console.print(f"[green]Sample dataset created: {output_path}[/green]")
    return 0


def cmd_feedback(args: argparse.Namespace) -> int:
    """Add feedback to LangSmith command."""
    from dataagent_harbor.tracing import TracingManager
    
    tracing = TracingManager()
    
    if not tracing.enabled:
        console.print("[red]LangSmith tracing is not enabled[/red]")
        console.print("Set LANGSMITH_API_KEY and LANGSMITH_TRACING_V2=true")
        return 1
    
    job_dir = Path(args.job_dir)
    report_json = job_dir / "report.json"
    
    if not report_json.exists():
        console.print(f"[red]Report not found: {report_json}[/red]")
        return 1
    
    with open(report_json, "r", encoding="utf-8") as f:
        report_data = json.load(f)
    
    results = report_data.get("results", [])
    
    console.print(f"Adding feedback for {len(results)} results...")
    
    counts = tracing.add_batch_feedback(
        results=results,
        project_name=args.project_name,
    )
    
    console.print(f"[green]Success: {counts['success']}[/green]")
    console.print(f"[yellow]Skipped: {counts['skipped']}[/yellow]")
    console.print(f"[red]Errors: {counts['error']}[/red]")
    
    return 0


def main() -> int:
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="DataAgent Harbor - Testing and evaluation framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands", required=True)
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run benchmark")
    run_parser.add_argument(
        "--dataset", "-d",
        type=str,
        required=True,
        help="Path to dataset JSON file",
    )
    run_parser.add_argument(
        "--server", "-s",
        type=str,
        help="DataAgent Server URL (default: http://localhost:8000)",
    )
    run_parser.add_argument(
        "--api-key",
        type=str,
        help="API key for authentication",
    )
    run_parser.add_argument(
        "--concurrency", "-c",
        type=int,
        default=1,
        help="Number of concurrent requests (default: 1)",
    )
    run_parser.add_argument(
        "--limit", "-n",
        type=int,
        help="Limit number of questions to run",
    )
    run_parser.add_argument(
        "--jobs-dir",
        type=str,
        default="jobs",
        help="Directory to store job results (default: jobs)",
    )
    run_parser.add_argument(
        "--websocket", "-w",
        action="store_true",
        help="Use WebSocket instead of REST API",
    )
    run_parser.add_argument(
        "--trace", "-t",
        action="store_true",
        help="Enable LangSmith tracing",
    )
    
    # Report command
    report_parser = subparsers.add_parser("report", help="Generate report")
    report_parser.add_argument(
        "--job-dir", "-j",
        type=str,
        required=True,
        help="Path to job directory",
    )
    report_parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["summary", "json", "markdown"],
        default="summary",
        help="Output format (default: summary)",
    )
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze results")
    analyze_parser.add_argument(
        "--job-dir", "-j",
        type=str,
        required=True,
        help="Path to job directory",
    )
    analyze_parser.add_argument(
        "--failed-only",
        action="store_true",
        help="Show only failed tests",
    )
    analyze_parser.add_argument(
        "--category",
        type=str,
        help="Filter by category",
    )
    analyze_parser.add_argument(
        "--limit", "-n",
        type=int,
        help="Limit number of results to show",
    )
    
    # Create dataset command
    create_parser = subparsers.add_parser("create-dataset", help="Create sample dataset")
    create_parser.add_argument(
        "--output", "-o",
        type=str,
        default="sample-dataset.json",
        help="Output file path (default: sample-dataset.json)",
    )
    create_parser.add_argument(
        "--name",
        type=str,
        help="Dataset name",
    )
    
    # Feedback command
    feedback_parser = subparsers.add_parser("feedback", help="Add feedback to LangSmith")
    feedback_parser.add_argument(
        "--job-dir", "-j",
        type=str,
        required=True,
        help="Path to job directory",
    )
    feedback_parser.add_argument(
        "--project-name",
        type=str,
        help="LangSmith project name",
    )
    
    args = parser.parse_args()
    
    # Route to command
    if args.command == "run":
        return cmd_run(args)
    elif args.command == "report":
        return cmd_report(args)
    elif args.command == "analyze":
        return cmd_analyze(args)
    elif args.command == "create-dataset":
        return cmd_create_dataset(args)
    elif args.command == "feedback":
        return cmd_feedback(args)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
