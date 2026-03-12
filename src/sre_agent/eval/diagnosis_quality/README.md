# Diagnosis Quality Evaluation

This suite checks whether the agent produces a correct diagnosis.

## What it evaluates

The metrics are:

- `root_cause_correctness`: LLM-judge check that predicted and expected root causes align.
- `suggested_fixes_quality`: LLM-judge check that suggested fixes are correct and actionable.
- `affected_services_match`: deterministic overlap score between predicted and expected services.

## Execution model

The run is hybrid:

- GitHub MCP calls are real.
- Slack and CloudWatch tools are mocked.
- Agent output fields are scored, not tool-call order.

## Dataset shape

Test cases are loaded from:

- `src/sre_agent/eval/diagnosis_quality/dataset/test_cases`

Each case follows `DiagnosisQualityEvalCase` in:

- `src/sre_agent/eval/diagnosis_quality/dataset/schema.py`

Key fields:

- `case_id`
- `service_name`
- `github_owner`, `github_repo`, `github_ref`
- `mock_cloudwatch_entries`
- `expected_root_cause`
- `expected_fix_suggestion_mentions`
- `expected_affected_services`

## Run

Required environment:

- `ANTHROPIC_API_KEY`
- `GITHUB_PERSONAL_ACCESS_TOKEN`

If you are running Opik locally, start the Opik platform first:

```bash
# Clone the Opik repository
git clone https://github.com/comet-ml/opik.git

# Navigate to the repository
cd opik

# Start the Opik platform
./opik.sh
```

See [comet-ml/opik](https://github.com/comet-ml/opik) for details.

When the server is running, open [http://localhost:5173/](http://localhost:5173/) to view datasets and experiments.

Run command:

```bash
uv sync --group eval
uv run sre-agent-run-diagnosis-quality-eval
```
