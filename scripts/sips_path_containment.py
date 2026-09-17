"""Shared path-containment policy for all SIPS record, evidence and context paths.

Every path that crosses from user-controlled or model-controlled input into a
SIPS store, evidence file, or distill source is resolved here. Resolution is
canonical (symlinks expanded, ``..`` collapsed) and membership is verified
against an explicit allow-root list. The allow-root list is provided by the
caller — never by the same input path — so a malicious path cannot extend it.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable


class PathEscapeError(ValueError):
    """A resolved path is not contained within any configured allow-root."""


def _real(path: Path) -> Path:
    """Canonical real path, tolerating paths that do not exist yet."""
    try:
        return path.resolve(strict=False)
    except (OSError, RuntimeError):
        return path.expanduser().resolve(strict=False)


def _nests(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def canonical_within(
    value: str | os.PathLike[str],
    *,
    allowed_roots: Iterable[str | os.PathLike[str]] | None = None,
    allowed_roots_fallback: Iterable[str | os.PathLike[str]] | None = None,
) -> Path:
    """Return the canonical form of ``value`` and assert root containment.

    Relative paths are anchored under the first allowed root before
    canonicalization, so the caller's current working directory never becomes
    part of the resolution. Absolute paths must nest under a configured root.
    """
    raw = Path(value)
    if not str(value).strip():
        raise PathEscapeError("path value is empty or whitespace-only")
    roots = list(allowed_roots or [])
    fallback = list(allowed_roots_fallback or [])

    for root in roots:
        root_real = _real(Path(root))
        if raw.is_absolute():
            target = _real(raw)
            if _nests(target, root_real):
                return target
        else:
            anchored = _real(root_real / raw)
            if _nests(anchored, root_real):
                return anchored

    for root in fallback:
        root_real = _real(Path(root))
        target = _real(raw) if raw.is_absolute() else _real(root_real / raw)
        if _nests(target, root_real):
            return target

    raise PathEscapeError(
        f"path {str(value)!r} resolved to {str(_real(raw))!r}, "
        f"which is not under any configured root "
        f"{[str(r) for r in roots + fallback]}"
    )


def assert_within(value: str | os.PathLike[str], *, allowed_roots: Iterable[str | os.PathLike[str]]) -> Path:
    """Containment check for paths that must already exist or be writable."""
    target = _real(Path(value))
    for root in allowed_roots:
        if _nests(target, _real(Path(root))):
            return target
    raise PathEscapeError(
        f"path {str(value)!r} is not under allowed roots "
        f"{[str(r) for r in allowed_roots]}"
    )
