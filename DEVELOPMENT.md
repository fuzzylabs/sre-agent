# Developer Readme

This document contains documentation intended for developers of sre-agent.

Pre-requisites:

- [Docker](https://docs.docker.com/engine/install/)

> Note: In order for the pre-commit hooks to function properly, your Docker daemon should be running during setup.

## Developer environment setup

To work on the sre-agent as a developer, you'll need to configure your local development environment. You can do this by simply running:
```bash
make project-setup
```
This will install Python `3.12` using PyEnv, create a virtual environment using uv, and install the pre-commit hooks.

> Note: The `project-setup` process will check whether `pre-commits`, and `uv` are installed. If not, it will ask to install them on your behalf as they're required to use this template.


A Makefile is just a usual text file to define a set of rules or instructions to run which can be run using the `make` command. To see the available make commands:
```bash
make help
```

## Testing

With the uv shell active (see above), you can run all the tests using:

```bash
make tests
```

Or specific tests:

```bash
python -m pytest tests/test_dummy.py
```
