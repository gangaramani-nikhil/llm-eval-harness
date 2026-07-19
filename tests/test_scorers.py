"""Tests for the deterministic scorers. Run: pytest tests/ -v"""

import pytest

from harness.scorers import contains, exact_match, json_structure, llm_judge, regex, score


class TestExactMatch:
    def test_passes_on_identical_strings(self):
        assert exact_match("Paris", "Paris").passed

    def test_strips_whitespace_by_default(self):
        assert exact_match("  Paris\n", "Paris").passed

    def test_fails_on_difference(self):
        result = exact_match("Lyon", "Paris")
        assert not result.passed
        assert "Lyon" in result.reason

    def test_case_sensitive(self):
        assert not exact_match("paris", "Paris").passed


class TestContains:
    def test_passes_when_substring_present(self):
        assert contains("tests catch regressions early", "regressions").passed

    def test_case_insensitive_by_default(self):
        assert contains("It catches REGRESSIONS", "regressions").passed

    def test_case_sensitive_when_requested(self):
        assert not contains("It catches REGRESSIONS", "regressions", case_sensitive=True).passed

    def test_fails_when_missing(self):
        result = contains("nothing relevant here", "regressions")
        assert not result.passed
        assert "missing" in result.reason


class TestRegex:
    def test_passes_on_match(self):
        assert regex("ENG-1234", r"^ENG-\d{4}$").passed

    def test_fails_on_no_match(self):
        assert not regex("ticket ENG-1234 please", r"^ENG-\d{4}$").passed

    def test_multiline_output(self):
        assert regex("header\nresult: 42", r"result: \d+").passed


class TestJsonStructure:
    def test_passes_with_all_keys(self):
        output = '{"id": 42, "name": "Ada", "address": {"city": "London"}}'
        assert json_structure(output, ["id", "name", "address.city"]).passed

    def test_fails_on_invalid_json(self):
        result = json_structure("not json at all", ["id"])
        assert not result.passed
        assert "not valid JSON" in result.reason

    def test_fails_on_missing_key(self):
        result = json_structure('{"id": 42}', ["id", "name"])
        assert not result.passed
        assert "name" in result.reason

    def test_fails_on_missing_nested_key(self):
        result = json_structure('{"address": {"zip": "E1"}}', ["address.city"])
        assert not result.passed


class TestDispatch:
    def test_score_dispatches_by_type(self):
        result = score("hello world", {"type": "contains", "value": "world"})
        assert result.passed and result.scorer == "contains"

    def test_unknown_scorer_raises(self):
        with pytest.raises(ValueError, match="unknown scorer"):
            score("x", {"type": "vibes"})

    def test_llm_judge_is_explicitly_not_implemented(self):
        with pytest.raises(NotImplementedError):
            llm_judge("some output", "some rubric")
