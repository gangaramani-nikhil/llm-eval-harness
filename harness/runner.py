"""Runner: load YAML cases, execute them against a provider, score the outputs."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import yaml

from .scorers import Score, score


@dataclass
class Case:
    name: str
    prompt: str
    scorer: dict[str, Any]
    # Lets the mock provider replay a fixed response so examples/tests run
    # with no API key. Ignored by real providers.
    mock_response: str | None = None


@dataclass
class CaseResult:
    case: Case
    output: str
    score: Score | None
    error: str | None = None

    @property
    def passed(self) -> bool:
        return self.error is None and self.score is not None and self.score.passed


class Provider(Protocol):
    def complete(self, prompt: str) -> str: ...


class MockProvider:
    """Key-free provider for tests and demos.

    Replays each case's `mock_response` if given, otherwise echoes a
    deterministic string so runs are still reproducible.
    """

    def __init__(self, responses: dict[str, str] | None = None):
        self.responses = responses or {}

    @classmethod
    def from_cases(cls, cases: list[Case]) -> "MockProvider":
        return cls({c.prompt: c.mock_response for c in cases if c.mock_response is not None})

    def complete(self, prompt: str) -> str:
        return self.responses.get(prompt, f"[mock response to: {prompt[:60]}]")


class OpenAIProvider:
    """Minimal OpenAI chat-completions provider. Requires OPENAI_API_KEY."""

    def __init__(self, model: str = "gpt-4o-mini"):
        from openai import OpenAI  # imported lazily so tests don't need the dep

        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set (see .env.example)")
        self.client = OpenAI()
        self.model = model

    def complete(self, prompt: str) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        return resp.choices[0].message.content or ""


def load_cases(path: str | Path) -> list[Case]:
    """Load a YAML case file: a list of {name, prompt, scorer, mock_response?}."""
    raw = yaml.safe_load(Path(path).read_text())
    if not isinstance(raw, list):
        raise ValueError(f"{path}: expected a YAML list of cases")
    cases = []
    for i, item in enumerate(raw):
        try:
            cases.append(
                Case(
                    name=item["name"],
                    prompt=item["prompt"],
                    scorer=item["scorer"],
                    mock_response=item.get("mock_response"),
                )
            )
        except (KeyError, TypeError) as exc:
            raise ValueError(f"{path}: case #{i + 1} is missing a field: {exc}") from exc
    return cases


def run_cases(cases: list[Case], provider: Provider) -> list[CaseResult]:
    results = []
    for case in cases:
        try:
            output = provider.complete(case.prompt)
        except Exception as exc:  # provider failure = failed case, not a crash
            results.append(CaseResult(case, output="", score=None, error=f"{type(exc).__name__}: {exc}"))
            continue
        try:
            result_score = score(output, case.scorer)
        except Exception as exc:
            results.append(CaseResult(case, output=output, score=None, error=f"scorer error: {exc}"))
            continue
        results.append(CaseResult(case, output=output, score=result_score))
    return results


def get_provider(name: str, model: str = "gpt-4o-mini") -> Provider:
    if name == "mock":
        return MockProvider()
    if name == "openai":
        return OpenAIProvider(model=model)
    raise ValueError(f"unknown provider {name!r} (have: mock, openai)")
