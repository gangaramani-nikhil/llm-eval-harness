"""CLI entry point: python -m harness.cli --cases examples/cases.yaml --provider mock"""

from __future__ import annotations

import argparse
import sys

from .report import exit_code, print_report
from .runner import MockProvider, get_provider, load_cases, run_cases


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="llm-eval-harness",
        description="Run YAML prompt-regression cases against an LLM provider.",
    )
    parser.add_argument("--cases", required=True, help="path to a YAML case file")
    parser.add_argument(
        "--provider",
        default="mock",
        choices=["mock", "openai"],
        help="mock replays each case's mock_response (no API key needed)",
    )
    parser.add_argument("--model", default="gpt-4o-mini", help="model name for the openai provider")
    parser.add_argument("--verbose", action="store_true", help="print model outputs")
    args = parser.parse_args(argv)

    try:
        cases = load_cases(args.cases)
    except (OSError, ValueError) as exc:
        print(f"error loading cases: {exc}", file=sys.stderr)
        return 2

    if args.provider == "mock":
        provider = MockProvider.from_cases(cases)
    else:
        try:
            provider = get_provider(args.provider, model=args.model)
        except (RuntimeError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

    results = run_cases(cases, provider)
    print_report(results, show_output=args.verbose)
    return exit_code(results)


if __name__ == "__main__":
    raise SystemExit(main())
