# llm-eval-harness

Prompt regression testing for LLM outputs. The unglamorous 80% of working with
LLMs — checking that a prompt tweak didn't silently break something — made into
a small tool.

## The problem

You tweak a prompt to fix one edge case, ship it, and a week later notice three
other behaviors quietly regressed. LLM outputs are non-deterministic enough that
"it looked fine when I tried it" doesn't scale. This harness lets you write the
behaviors you care about down as test cases, run them against a model, and get a
pass/fail report with a CI-friendly exit code — the same workflow as unit tests,
applied to prompts.

## How it works

```
YAML case files ──► runner ──► provider (mock | openai) ──► scorers ──► report + exit code
```

- **Cases** live in YAML: a name, a prompt, and a scorer config.
- **Runner** sends each prompt to a provider and scores the output. Provider
  failures fail the case instead of crashing the run.
- **Scorers** are deterministic checks: `exact_match`, `contains`, `regex`,
  `json_structure` (parses JSON, checks required keys incl. dotted nested paths).
- **Report** prints a pass/fail table and exits nonzero on any failure, so CI
  can block a merge on a regression.

## Status

Early — building in public. The core loop (YAML → run → score → report → exit
code) works and is tested. The mock provider means the whole thing runs with no
API key. The OpenAI provider is minimal (one system-less user message,
temperature 0) and will grow. Expect rough edges.

## Setup

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Run the examples key-free (mock provider replays each case's `mock_response`):

```bash
python -m harness.cli --cases examples/cases.yaml
```

Run against a real model:

```bash
cp .env.example .env   # add your OPENAI_API_KEY
set -a && source .env && set +a
python -m harness.cli --cases examples/cases.yaml --provider openai --model gpt-4o-mini
```

Run the tests:

```bash
pytest tests/ -v
```

## Example case

```yaml
- name: extract-ticket-id
  prompt: "Extract the ticket ID from: 'Follow up on ENG-1234 about the login bug.' Reply with only the ID."
  mock_response: "ENG-1234"          # replayed by the mock provider; ignored by real providers
  scorer:
    type: regex
    pattern: "^ENG-\\d{4}$"
```

## Using it in CI

`python -m harness.cli --cases cases.yaml --provider openai` exits `0` when
every case passes and `1` on any failure or provider error, so it drops into a
CI step directly. (A GitHub Actions workflow is on the roadmap — for now, wire
the command in yourself.)

## Roadmap

- [x] YAML case loading with validation
- [x] Provider interface + mock provider (key-free runs)
- [x] Deterministic scorers: `exact_match`, `contains`, `regex`, `json_structure`
- [x] CLI report with pass/fail table and CI exit codes
- [x] Test suite (scorers + end-to-end runner)
- [ ] LLM-as-judge scorer (rubric-based; stub raises `NotImplementedError`)
- [ ] Full JSON Schema validation (types, constraints — current check is keys-only)
- [ ] Prompt templates with variables, so cases share one prompt with different inputs
- [ ] Baseline snapshots: diff outputs against a saved baseline, not just assertions
- [ ] GitHub Actions workflow example
- [ ] Latency/cost tracking per case
- [ ] More providers (Anthropic, local models via Ollama)
