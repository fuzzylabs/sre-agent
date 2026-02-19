# SRE Agent Evaluation

This directory contains evaluation suites for the SRE agent.

## Scope

Evaluations use intentionally flawed service snippets from:

- [sre-agent-eval](https://github.com/fuzzylabs/sre-agent-eval)

Evaluations are implemented with Opik.

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

From the project root:

```bash
uv run sre-agent-run-tool-call-eval
```

For suite-specific details, see:

- `src/sre_agent/eval/tool_call/README.md`
