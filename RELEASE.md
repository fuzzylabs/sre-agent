# Release Guide

This document describes the process for creating a new release of `sre-agent`.

## Prerequisites

- You have push access to the repository.
- All features and fixes intended for the release have been merged into `main`.
- CI is passing on `main`.

## Steps

### 1. Create a release branch

Branch off `main` using the `release/` prefix:

```bash
git checkout main
git pull origin main
git checkout -b release/vX.Y.Z
```

### 2. Bump the version

Update the version in `pyproject.toml`:

```toml
version = "X.Y.Z"
```

Commit the version bump:

```bash
git add pyproject.toml
git commit -m "Bump version to vX.Y.Z"
```

### 3. Open a pull request

Push the release branch and open a PR against `main`:

```bash
git push -u origin release/vX.Y.Z
```

Ensure CI passes and get the required approvals.

### 4. Merge and tag

Once the PR is approved, merge it into `main` via GitHub. Then tag the merge commit locally:

```bash
git checkout main
git pull origin main
git tag vX.Y.Z
git push origin vX.Y.Z
```

### 5. Publish to PyPI

Publishing happens automatically via GitHub Actions when a `v*` tag is pushed
(see `.github/workflows/publish.yml`). The workflow uses
[Trusted Publishers](https://docs.pypi.org/trusted-publishers/) so no API tokens
need to be stored as secrets.

Verify the release is live at https://pypi.org/project/sre-agent/.

### 6. Create a GitHub release

Create a release on GitHub from the new tag:

```bash
gh release create vX.Y.Z --generate-notes --title "vX.Y.Z"
```

Review and edit the auto-generated notes as needed.

## Versioning

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR** — incompatible API or behaviour changes
- **MINOR** — new functionality, backwards-compatible
- **PATCH** — backwards-compatible bug fixes

## Hotfixes

For urgent fixes against a release that is already published:

```bash
git checkout main
git pull origin main
git checkout -b hotfix/vX.Y.Z
```

Follow the same process: bump version, open a PR, merge, tag, and create a GitHub release.
