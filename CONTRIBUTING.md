# 🧑‍💻 Contributing to `sre-agent`

Welcome to sre-agent! This document contains the instructions on how to contribute to sre-agent.

## 🔥 Quicklinks

* [Getting Started](#getting-started)
  * [Issues](#issues)
  * [Pull Requests](#pull-requests)

## 🎬 Getting started

Contributions are made to this project using Issues and Pull Request (PRs). Before creating your own, search for existing Issues and PRs - as I'm sure you're aware, this removes duplication and makes everyone's life easier!

### 😭 Issues

Issues should be used to report bugs with `sre-agent`, proposing new features before a PR is raised, and to request new features.

If you find an issue that has already been reported by another good samaritan, then please add your own reproduction information to the existing issue rather than creating a new one. Reacting to issues can also help our maintainers understand that the issue is affecting more than one reporter.

### 🎫 Pull Requests

Pull Requests (PRs) are how contributions are made to `sre-agent` and are always welcome.

The preferred way to contribute to `sre-agent` is to fork the main repository on Github and then submit a pull request.

#### 🖥️ Getting setup locally

Here, we'll explain to get setup locally with `sre-agent` and how to set up your git repository:

1. If you don't already have one, [create an account](https://github.com/join) on Github.

2. Fork the repository by clicking on the 'fork' button near the top of the page. What this will do is create a copy of the `sre-agent` repository under your Github account. See [here](https://help.github.com/articles/fork-a-repo/) for a guide on how to fork a repository.

3. Clone this forked version of `sre-agent` to your local disk:

```bash
git clone git@github.com:<your_username>/sre-agent.git
cd sre-agent
```

4. Add the `upstream` remote. Adding this means you can keep your repository sync'd with the latest changes to the main repository:

```bash
git remote add upstream git@github.com:fuzzylabs/sre-agent.git
```

5. Check that these remote aliases are correctly configured by running: `git remote -v`, this should show the following:

```bash
origin  git@github.com:<your_username>/sre-agent.git (fetch)
origin  git@github.com:<your_username>/sre-agent.git (push)
upstream        git@github.com:fuzzylabs/sre-agent.git (fetch)
upstream        git@github.com:fuzzylabs/sre-agent.git (push)
```

Now you have git properly configured, you can install the development dependencies which are described in [DEVELOPMENT.md](https://github.com/fuzzylabs/sre-agent/blob/main/DEVELOPMENT.md). Once the development environment is setup, you can start making changes by following these steps:

6. Sync your `main` branch with the `upstream/main` branch:

```bash
git checkout main
git fetch upstream
git merge upstream/main
```

7. Create your feature branch which will contain your development changes:

```bash
git checkout -b <your_feature>
```

and you can now start making changes! We're sure that you don't need reminding but it's good practise to never work on the `main` branch and to always use a feature branch. The [DEVELOPMENT.md](https://github.com/fuzzylabs/sre-agent/blob/main/DEVELOPMENT.md) guide tells you how to run tests.

8. Develop your feature on your computer and when you're done editing, add the changed files to git and then commit:

```bash
git add <modified_files>
git commit -m '<a meaningful commit message>'
```

Once committed, push your changes to your Github account:

```bash
git push -u origin <your_feature>
```

9. Once you're finished and ready to make a pull request to the main repository, then follow the [steps below](#🤔-making-a-pull-request)

#### 🤔 Making a pull request

Before a PR can be merged, two core developers need to approve it. It may be the case that you have an incomplete contribution, where you're expecting to do more work before receiving a full review, and these should have the prefix `[WIP]` - this will indicate to everyone that it is a work in progress ticket and will avoid duplicated work. These types of PRs often benefit from including a task list in the PR description.

It's important to do the following, and the PR template that you'll see will ask you explicitly:

* Give your pull request a helpful title which summarises what your contribution does.

* Make sure your code passes the tests. At the moment, running the whole test suite doesn't take a long time so we advice doing that with `pytest` (see the [DEVELOPMENT.md](https://github.com/fuzzylabs/sre-agent/blob/main/DEVELOPMENT.md) guide).

* Your PR will also be checked for spelling errors in the CI by the [`typos`](https://github.com/crate-ci/typos) crate. If a false positive is raised by the checker, consider adding it to the `.typos.toml` file in the root of the project.

* Ensure that your code is documented and commented, and that the documentation renders properly.
