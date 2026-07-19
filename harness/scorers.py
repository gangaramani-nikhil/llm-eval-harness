"""Scorers: deterministic checks on LLM outputs.

Each scorer takes the model output plus the case's `scorer` config dict and
returns a Score. Scorers are intentionally simple and deterministic so a
failing score means something reproducible broke.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Score:
    passed: bool
    scorer: str
    reason: str


def exact_match(output: str, expected: str, strip: bool = True, **_: Any) -> Score:
    got = output.strip() if strip else output
    want = expected.strip() if strip else expected
    passed = got == want
    reason = "exact match" if passed else f"expected {want!r}, got {got!r}"
    return Score(passed, "exact_match", reason)


def contains(output: str, value: str, case_sensitive: bool = False, **_: Any) -> Score:
    haystack = output if case_sensitive else output.lower()
    needle = value if case_sensitive else value.lower()
    passed = needle in haystack
    reason = f"contains {value!r}" if passed else f"missing {value!r}"
    return Score(passed, "contains", reason)


def regex(output: str, pattern: str, **_: Any) -> Score:
    passed = re.search(pattern, output, flags=re.DOTALL) is not None
    reason = f"matches /{pattern}/" if passed else f"no match for /{pattern}/"
    return Score(passed, "regex", reason)


def _walk(data: Any, path: list[str]) -> tuple[bool, Any]:
    """Walk a dotted key path through nested dicts. Returns (found, value)."""
    node = data
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return False, None
        node = node[key]
    return True, node


def json_structure(output: str, required_keys: list[str], **_: Any) -> Score:
    """Structural check: output parses as JSON and contains the required keys.

    `required_keys` supports dotted paths for nested dicts, e.g. "user.name".
    This is deliberately not full JSON Schema (no types/constraints yet) —
    see the roadmap.
    """
    try:
        data = json.loads(output)
    except json.JSONDecodeError as exc:
        return Score(False, "json_structure", f"output is not valid JSON: {exc}")

    missing = [k for k in required_keys if not _walk(data, k.split("."))[0]]
    if missing:
        return Score(False, "json_structure", f"missing keys: {', '.join(missing)}")
    return Score(True, "json_structure", f"all {len(required_keys)} required keys present")


def llm_judge(output: str, rubric: str, **_: Any) -> Score:
    """TODO: score output against a rubric using a judge model.

    Planned design: call the configured provider with the rubric + output,
    ask for a 1-5 score plus justification, pass if >= threshold. Needs a
    provider passed in, which the current scorer signature doesn't support —
    that's part of why it's not done yet.
    """
    raise NotImplementedError(
        "llm_judge is not implemented yet — see README roadmap. "
        "Use exact_match/contains/regex/json_structure for now."
    )


SCORERS: dict[str, Callable[..., Score]] = {
    "exact_match": exact_match,
    "contains": contains,
    "regex": regex,
    "json_structure": json_structure,
    "llm_judge": llm_judge,
}


def score(output: str, config: dict[str, Any]) -> Score:
    """Dispatch a case's scorer config, e.g. {type: contains, value: "paris"}."""
    config = dict(config)
    scorer_type = config.pop("type", None)
    fn = SCORERS.get(scorer_type)
    if fn is None:
        raise ValueError(f"unknown scorer type: {scorer_type!r} (have: {sorted(SCORERS)})")
    return fn(output, **config)
