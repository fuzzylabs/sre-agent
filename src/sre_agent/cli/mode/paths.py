"""Path helpers for the CLI."""

from pathlib import Path


def project_root() -> Path:
    """Return the repository root directory.

    Returns:
        The repository root directory path.
    """
    return Path(__file__).resolve().parents[4]
