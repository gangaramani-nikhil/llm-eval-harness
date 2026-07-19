"""End-to-end tests: YAML loading, mock-provider runs, report exit codes."""

import pytest

from harness.report import exit_code
from harness.runner import Case, MockProvider, load_cases, run_cases

EXAMPLES = "examples/cases.yaml"


def test_example_cases_file_loads():
    cases = load_cases(EXAMPLES)
    assert len(cases) == 4
    assert all(c.name and c.prompt and c.scorer for c in cases)


def test_example_cases_all_pass_with_mock_provider():
    cases = load_cases(EXAMPLES)
    results = run_cases(cases, MockProvider.from_cases(cases))
    assert all(r.passed for r in results)
    assert exit_code(results) == 0


def test_regression_produces_nonzero_exit():
    cases = [Case(name="c", prompt="p", scorer={"type": "exact_match", "expected": "old"}, mock_response="old")]
    results = run_cases(cases, MockProvider.from_cases(cases))
    assert exit_code(results) == 0

    # Simulate a prompt change regressing the output:
    results = run_cases(cases, MockProvider({"p": "something else entirely"}))
    assert exit_code(results) == 1


def test_provider_exception_fails_case_without_crashing():
    class BrokenProvider:
        def complete(self, prompt):
            raise ConnectionError("no network")

    results = run_cases([Case(name="c", prompt="p", scorer={"type": "contains", "value": "x"})], BrokenProvider())
    assert not results[0].passed
    assert "ConnectionError" in results[0].error
    assert exit_code(results) == 1


def test_load_cases_rejects_missing_fields(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("- name: no-prompt-here\n")
    with pytest.raises(ValueError, match="missing a field"):
        load_cases(bad)


def test_empty_results_fail_closed():
    assert exit_code([]) == 1
