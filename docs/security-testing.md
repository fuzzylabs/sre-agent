# Security Tests

Inside the [`tests`](tests) directory are a collection of [security tests](/tests/security_tests) that can be run to ensure defences against possible prompt-injection threats against the agent. Agentic systems can be vulnerable to prompt-injection attacks where an attacker can manipulate the input to the agent to perform unintended actions. These tests are designed to ensure that the agent is robust against such attacks.

To run the security tests, first launch the agent using the `compose.tests.yaml` file:

```bash
docker compose -f compose.tests.yaml up --build
```

Then, in a separate terminal, run the security tests:

```bash
uv run pytest tests/security_tests
```

We are currently testing for the following vulnerabilities:

- [X] Prompt Injection via `/diagnose` endpoint
- [X] Prompt Injection via Kubernetes logs
- [ ] Prompt Injection via application
- [X] Prompt Injection via GitHub files
