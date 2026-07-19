"""Report: print a pass/fail table and derive a CI-friendly exit code."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from .runner import CaseResult

console = Console()


def print_report(results: list[CaseResult], show_output: bool = False) -> None:
    table = Table(title="llm-eval-harness results")
    table.add_column("case", style="bold")
    table.add_column("result")
    table.add_column("scorer")
    table.add_column("detail", style="dim", overflow="fold")

    for r in results:
        if r.error:
            status, scorer_name, detail = "[red]ERROR[/red]", "-", r.error
        elif r.score and r.score.passed:
            status, scorer_name, detail = "[green]PASS[/green]", r.score.scorer, r.score.reason
        else:
            status = "[red]FAIL[/red]"
            scorer_name = r.score.scorer if r.score else "-"
            detail = r.score.reason if r.score else "no score"
        if show_output and r.output:
            detail += f"\noutput: {r.output[:200]}"
        table.add_row(r.case.name, status, scorer_name, detail)

    console.print(table)
    passed = sum(1 for r in results if r.passed)
    style = "green" if passed == len(results) else "red"
    console.print(f"[{style}]{passed}/{len(results)} passed[/{style}]")


def exit_code(results: list[CaseResult]) -> int:
    """0 if every case passed, 1 otherwise — wire this into CI to block merges."""
    return 0 if results and all(r.passed for r in results) else 1
