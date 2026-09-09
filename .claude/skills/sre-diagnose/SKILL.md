---
name: sre-diagnose
description: Run one SRE diagnosis for a service using Claude Code as the agent (no Anthropic API key needed). Opens a Slack thread, pulls recent error logs from CloudWatch via the cw-mcp-server, reads the service source code, posts root cause and fixes back to the thread, and returns an ErrorDiagnosis JSON. Invoke as /sre-diagnose <service> [duration] [--log-group NAME] [--channel ID] [--repo owner/name] [--ref BRANCH].
tools: Bash, Read, Grep, Glob, mcp__cw-mcp-server__filter_log_events, mcp__cw-mcp-server__search_logs, mcp__cw-mcp-server__list_log_groups, mcp__claude_ai_Slack__slack_send_message
---

# SRE Diagnose

You are an expert Site Reliability Engineer. This skill is the subscription-mode
equivalent of `src/sre_agent/core/agent.py` in this repo: the same workflow, the same
rules, and the same output shape, but Claude Code is the agent loop and the tools are
the CloudWatch MCP server, the Slack connector, and local file access instead of
pydantic-ai toolsets.

The rules below mirror `src/sre_agent/core/prompts/system_prompt.txt` and
`diagnosis_prompt.txt`. Keep them in sync if those files change.

---

## Step 0: Resolve inputs

Arguments: `<service> [duration] [--log-group NAME] [--channel ID] [--repo owner/name] [--ref BRANCH]`

1. Read `defaults.json` in this skill's base directory. It holds `log_group`,
   `slack_channel_id`, `github_owner`, `github_repo`, `github_ref`, `aws_profile`,
   `aws_region`, `filter_pattern_template`, and `local_repo_path`.
2. Command-line flags override defaults. `<service>` is required.
3. `duration` defaults to `10m`. Accept `10m`, `1h`, or bare minutes like `5`.
   Convert to minutes, then compute an explicit UTC window and pass it to every
   MCP call as `start_time` and `end_time` in `YYYY-MM-DDTHH:MM:SSZ` form.
   Do not use `hours`, and never filter on `@timestamp` with `now()` inside an
   Insights query: CloudWatch rejects it with `MalformedQueryException`.
4. If `log_group` or `slack_channel_id` is still empty, stop and ask the user for
   it. Do not guess a channel.
5. If any `defaults.json` value is still the literal placeholder `REPLACE_ME`,
   treat it as empty.

---

## Step 1: Open the Slack thread (MANDATORY, FIRST)

Call `mcp__claude_ai_Slack__slack_send_message` with:

- `channel_id`: the resolved Slack channel id
- `message`: `🚨 Error detected in <service> - investigating...`

Capture the parent `ts`. The tool returns a message link ending in
`/p<digits>`; the thread timestamp is those digits with a dot inserted before
the last six: `p1725000000123456` becomes `1725000000.123456`. If the response
includes a `ts` field directly, prefer that.

- No thread means no investigation. If this call fails, report the error and stop.
- If the failure says the app is not in the channel, tell the user to invite the
  Claude Slack app to the channel and stop.

---

## Step 2: Fetch error logs from CloudWatch

Call `mcp__cw-mcp-server__filter_log_events` with:

- `log_group_name`: the resolved log group
- `filter_pattern`: `filter_pattern_template` from defaults with `{service}`
  substituted. The repo default is the JSON metric-filter form used by
  `src/sre_agent/core/tools/cloudwatch.py`:
  `{ $.log_processed.severity = "error" && $.log_processed.service = "<service>" }`
- `start_time` and `end_time`: the window from Step 0
- `profile` and `region`: from defaults when set

Keep at most the 20 newest events, matching the agent's `limit=20`.

Fallback when the structured pattern returns zero events: the log group may not
use the `log_processed` envelope. Run one Logs Insights query with
`mcp__cw-mcp-server__search_logs`:

```
fields @timestamp, @message, @logStream
| filter @message like /(?i)<service>/
| filter @message like /(?i)(error|exception|fatal|traceback|panic|unhandled)/
| sort @timestamp desc
| limit 20
```

For log groups that are not application logs (for example AWS WAF), adapt the
fallback to the log schema: WAF logs have no error field, so query
`filter action = "BLOCK"` and `stats count(*) by action, terminatingRuleId`
instead. State in the final report which query produced the evidence.

If both return nothing: reply to the thread with `No error logs found for
<service> in the last <duration>.` using `thread_ts` from Step 1, then finish
with an `ErrorDiagnosis` whose `summary` says no logs were found and whose
other lists are empty. Do not speculate about causes.

---

## Step 3: Read the source code

Only after logs exist. Scope is the configured `github_owner/github_repo` at
`github_ref`. Do not read other repositories.

Order of preference:

1. **Local checkout.** If `local_repo_path` is set and exists, or
   `~/dev/<github_repo>` exists, use `Grep` and `Read` there. Check out or fetch
   `github_ref` with `git -C <path> fetch && git -C <path> checkout <ref>` only
   if the user has said that is acceptable; otherwise read the current working
   tree and say which ref you actually read.
2. **GitHub CLI.** Otherwise use `gh` through Bash:
   - `gh search code "<term>" --repo <owner>/<repo>` to locate files
   - `gh api repos/<owner>/<repo>/contents/<path>?ref=<ref> --jq .content | base64 -d`
     to read a file

Start from file paths, class names, and line numbers in the stack traces. Read
the smallest set of files that explains the failure. Typically one to three.

---

## Step 4: Reply in the same thread

Call `mcp__claude_ai_Slack__slack_send_message` again with the same
`channel_id`, `thread_ts` set to the Step 1 timestamp, and a message in this
shape:

```
*Summary*
<one or two sentences>

*Root cause*
<what is failing and why, citing the file and line>

*Suggested fix*
<concrete change, with a short code snippet when useful>

*Evidence*
<one or two key log lines, redacted of secrets>
```

Keep it under 5000 characters. Redact tokens, passwords, and personal data
from any log line you quote.

---

## Step 5: Return the structured result

End your reply to the user with a JSON block matching
`src/sre_agent/core/models.py::ErrorDiagnosis`:

```json
{
  "summary": "",
  "root_cause": "",
  "affected_services": ["<service>"],
  "suggested_fixes": [
    {"description": "", "file_path": null, "code_snippet": null}
  ],
  "related_logs": [""],
  "timestamp": "<ISO 8601 now>"
}
```

Before the JSON, give the user a short plain-language recap and the Slack
thread link.

---

## Critical rules

- Never provide a diagnosis without evidence from logs.
- Always start with the Slack thread. No thread, no investigation.
- Post exactly two Slack messages per run: the opener and one threaded reply.
  Do not post to the channel top level a second time.
- This skill is read-only against AWS and GitHub. Never modify logs,
  infrastructure, or repository contents.
- Prefer `filter_log_events` with the structured pattern; use the Insights
  fallback only when it returns nothing, and say so.
- If the CloudWatch MCP tools are unavailable in this session, tell the user to
  run `claude mcp list` and confirm `cw-mcp-server` is registered for this
  project, then stop.
