# SRE Agent Evaluation

This directory contains evaluation suites for the SRE agent.

## Scope

Evaluations use intentionally flawed service snippets from:

- [sre-agent-eval](https://github.com/fuzzylabs/sre-agent-eval)

Evaluations are implemented with [Opik](https://github.com/comet-ml/opik).

## Structure

- `common`: shared helpers used across suites.
- `tool_call`: evaluates tool selection and tool call order.

## Current suite

The active suite is `tool_call`.

It validates:

- required tool usage
- expected tool order
- optional GitHub usage expectations per case

It uses:

- real GitHub MCP calls
- mocked Slack and CloudWatch calls
- Opik tool spans (`task_span`) for scoring

## Run

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

For suite-specific details, see:

- `src/sre_agent/eval/tool_call/README.md`
