# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for PID resolver."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from fdo_usecases.fdo_graph_renderer.pid_resolver import PIDResolver


def test_load_local_dtr_info_types():
    """Test loading InfoType definitions from local DTR."""
    with TemporaryDirectory() as tmpdir:
        dtr_path = Path(tmpdir)
        info_types_dir = dtr_path / "info_types"
        info_types_dir.mkdir()

        test_json = {
            "Identifier": "21.T11969/test123",
            "name": "testAttribute",
            "description": "A test attribute",
        }

        with open(info_types_dir / "test.json", "w") as f:
            json.dump(test_json, f)

        resolver = PIDResolver(dtr_path=dtr_path)

        assert "21.T11969/test123" in resolver.cache
        meta = resolver.cache["21.T11969/test123"]
        assert meta["name"] == "testAttribute"
        assert meta["description"] == "A test attribute"
        assert meta["source"] == "local"


def test_load_local_dtr_profiles():
    """Test loading Profile definitions from local DTR."""
    with TemporaryDirectory() as tmpdir:
        dtr_path = Path(tmpdir)
        profiles_dir = dtr_path / "profiles"
        profiles_dir.mkdir()

        test_json = {
            "Identifier": "21.T11969/profile123",
            "name": "TestProfile",
            "description": "A test profile",
        }

        with open(profiles_dir / "test.json", "w") as f:
            json.dump(test_json, f)

        resolver = PIDResolver(dtr_path=dtr_path)

        assert "21.T11969/profile123" in resolver.cache


def test_resolve_cached_pid():
    """Test resolving a PID that's in the cache."""
    with TemporaryDirectory() as tmpdir:
        dtr_path = Path(tmpdir)
        info_types_dir = dtr_path / "info_types"
        info_types_dir.mkdir()

        test_json = {
            "Identifier": "21.T11969/cached123",
            "name": "CachedAttribute",
            "description": "Already cached",
        }

        with open(info_types_dir / "cached.json", "w") as f:
            json.dump(test_json, f)

        resolver = PIDResolver(dtr_path=dtr_path)
        result = resolver.resolve("21.T11969/cached123")

        assert result["name"] == "CachedAttribute"
        assert result["source"] == "local"


def test_resolve_offline_returns_pid():
    """Test that offline mode returns PID when not in cache."""
    resolver = PIDResolver(offline=True)
    result = resolver.resolve("21.T11969/unknown123")

    assert result["name"] == "21.T11969/unknown123"
    assert result["description"] == ""
    assert result["source"] == "offline"


def test_resolve_uncached_offline():
    """Test resolving uncached PID in offline mode."""
    resolver = PIDResolver(offline=True)

    result = resolver.resolve("21.T11969/notindatabase")

    assert result["name"] == "21.T11969/notindatabase"
    assert result["description"] == ""


def test_get_name_convenience():
    """Test get_name convenience method."""
    with TemporaryDirectory() as tmpdir:
        dtr_path = Path(tmpdir)
        info_types_dir = dtr_path / "info_types"
        info_types_dir.mkdir()

        test_json = {
            "Identifier": "21.T11969/name123",
            "name": "TestName",
            "description": "Description",
        }

        with open(info_types_dir / "name.json", "w") as f:
            json.dump(test_json, f)

        resolver = PIDResolver(dtr_path=dtr_path)

        assert resolver.get_name("21.T11969/name123") == "TestName"


def test_get_description_convenience():
    """Test get_description convenience method."""
    with TemporaryDirectory() as tmpdir:
        dtr_path = Path(tmpdir)
        info_types_dir = dtr_path / "info_types"
        info_types_dir.mkdir()

        test_json = {
            "Identifier": "21.T11969/desc123",
            "name": "Name",
            "description": "Test Description",
        }

        with open(info_types_dir / "desc.json", "w") as f:
            json.dump(test_json, f)

        resolver = PIDResolver(dtr_path=dtr_path)

        assert resolver.get_description("21.T11969/desc123") == "Test Description"


def test_caching_avoids_duplicate_lookups():
    """Test that caching prevents duplicate network requests."""
    resolver = PIDResolver(offline=True)

    result1 = resolver.resolve("21.T11969/same123")
    result2 = resolver.resolve("21.T11969/same123")

    assert result1 is result2
    assert len(resolver.cache) == 1


@pytest.mark.skip(reason="Network test - run manually")
def test_network_resolution():
    """Test actual network resolution (skip in CI)."""
    resolver = PIDResolver(offline=False)
    result = resolver.resolve("21.T11969/bd3e9fb9b606d2198c9e")

    assert "name" in result
    assert result["source"] in ["network", "local", "fallback"]
