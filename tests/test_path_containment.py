"""Adversarial path containment tests — path traversal must be rejected."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from sips_path_containment import PathEscapeError, assert_within, canonical_within


@pytest.fixture
def sips_home(tmp_path: Path) -> Path:
    root = tmp_path / "sips"
    (root / "records").mkdir(parents=True)
    return root


def test_relative_path_within_allowed_root(sips_home: Path) -> None:
    assert canonical_within("records/foo.json", allowed_roots=[sips_home]) == sips_home / "records" / "foo.json"


def test_absolute_path_within_allowed_root(sips_home: Path) -> None:
    assert canonical_within(str(sips_home / "records" / "a.json"), allowed_roots=[sips_home]) == sips_home / "records" / "a.json"


def test_path_traversal_outside_root_is_rejected(sips_home: Path) -> None:
    outside = sips_home.parent / "secrets" / "exfil.json"
    with pytest.raises(PathEscapeError):
        canonical_within(f"../{outside.name}", allowed_roots=[sips_home])


def test_symlink_escape_outside_root_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    target = root / "evil"
    try:
        target.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation not permitted")
    with pytest.raises(PathEscapeError):
        canonical_within("evil/secret.json", allowed_roots=[root])


def test_absolute_escape_directly_is_rejected(sips_home: Path) -> None:
    with pytest.raises(PathEscapeError):
        canonical_within("/etc/passwd", allowed_roots=[sips_home])


def test_nested_child_path_is_contained(sips_home: Path) -> None:
    path = canonical_within("records/sub/child.json", allowed_roots=[sips_home])
    assert path == sips_home / "records" / "sub" / "child.json"


def test_empty_allowed_roots_with_absolute_still_rejected(tmp_path: Path) -> None:
    target = tmp_path / "file.json"
    target.write_text("{}")
    with pytest.raises(PathEscapeError):
        canonical_within(str(target), allowed_roots=[])


def test_fallback_root_accepts_absolute_match(sips_home: Path, tmp_path: Path) -> None:
    target = tmp_path / "store" / "m.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("{}")
    assert canonical_within(str(target), allowed_roots=[sips_home], allowed_roots_fallback=[tmp_path / "store"]) == target


def test_assert_within_accepts_existing_root_path(sips_home: Path) -> None:
    assert assert_within(str(sips_home / "records"), allowed_roots=[sips_home]) == sips_home / "records"


def test_assert_within_rejects_outside_path(sips_home: Path) -> None:
    with pytest.raises(PathEscapeError):
        assert assert_within("/etc/hosts", allowed_roots=[sips_home])


def test_alternate_separator_style_is_normalized(sips_home: Path) -> None:
    path = canonical_within("records//sub/../a.json", allowed_roots=[sips_home])
    assert path == sips_home / "records" / "a.json"


def test_falsy_path_raises_or_falls_back(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    with pytest.raises((PathEscapeError, ValueError)):
        canonical_within("", allowed_roots=[root])


def test_multiple_roots_accept_first_match(sips_home: Path, tmp_path: Path) -> None:
    a = tmp_path / "a"
    a.mkdir()
    result = canonical_within(str(a / "file.json"), allowed_roots=[sips_home, tmp_path])
    assert result == a / "file.json"
