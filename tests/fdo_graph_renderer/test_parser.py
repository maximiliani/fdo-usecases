# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for FDO graph parser."""

import json

from fdo_usecases.fdo_graph_renderer.parser import FDOParser, FDORecord


def test_parse_zenodo_fdos():
    """Test parsing Zenodo FDO records."""
    sample_data = {
        "10.5281/zenodo.123": {
            "pid": "10.5281/zenodo.123",
            "record": [
                {"key": "21.T11969/bd3e9fb9b606d2198c9e", "value": "Test Dataset"},
                {
                    "key": "21.T11969/7c67083a5d218e544063",
                    "value": "0000-0001-2345-6789",
                },
            ],
        },
        "10.5281/zenodo.456": {
            "pid": "10.5281/zenodo.456",
            "record": [
                {"key": "21.T11969/bd3e9fb9b606d2198c9e", "value": "Another Dataset"},
            ],
        },
    }

    parser = FDOParser()
    records = parser.parse(sample_data)

    assert len(records) == 2
    assert all(isinstance(r, FDORecord) for r in records)
    assert any(r.pid == "10.5281/zenodo.123" for r in records)
    assert any(r.node_type == "zenodo" for r in records)


def test_parse_md5_files():
    """Test parsing MD5 file FDOs."""
    sample_data = {
        "md5:abc123": {
            "pid": "md5:abc123",
            "record": [
                {"key": "21.T11969/a80ed2ef79e22f1d8af8", "value": "md5:abc123"},
                {"key": "21.T11969/bd3e9fb9b606d2198c9e", "value": "data.txt"},
            ],
        },
    }

    parser = FDOParser()
    records = parser.parse(sample_data)

    assert len(records) == 1
    assert records[0].node_type == "md5"


def test_detect_relationships():
    """Test that relationships are correctly detected."""
    sample_data = {
        "10.5281/zenodo.123": {
            "pid": "10.5281/zenodo.123",
            "record": [
                {
                    "key": "21.T11969/7f1a6afddcfeefbf195b",
                    "value": "10.5281/zenodo.456",
                },
                {"key": "21.T11969/bd3e9fb9b606d2198c9e", "value": "Not a PID"},
            ],
        },
        "10.5281/zenodo.456": {
            "pid": "10.5281/zenodo.456",
            "record": [],
        },
    }

    parser = FDOParser()
    records = parser.parse(sample_data)

    zenodo_123 = next(r for r in records if r.pid == "10.5281/zenodo.123")

    rel_attrs = [a for a in zenodo_123.attributes if a.is_relationship]
    non_rel_attrs = [a for a in zenodo_123.attributes if not a.is_relationship]

    assert len(rel_attrs) == 1
    assert rel_attrs[0].value == "10.5281/zenodo.456"
    assert len(non_rel_attrs) == 1
    assert non_rel_attrs[0].value == "Not a PID"


def test_classify_node_types():
    """Test node type classification."""
    parser = FDOParser()

    assert parser._classify_node("10.5281/zenodo.123") == "zenodo"
    assert parser._classify_node("md5:abc123") == "md5"
    assert parser._classify_node("21.T11969/abc123") == "handle"
    assert parser._classify_node("doi:10.1234/test") == "other"


def test_parse_file(tmp_path):
    """Test parsing from a file."""
    sample_data = {
        "10.5281/zenodo.123": {
            "pid": "10.5281/zenodo.123",
            "record": [],
        },
    }

    json_file = tmp_path / "test.json"
    with open(json_file, "w") as f:
        json.dump(sample_data, f)

    parser = FDOParser()
    records = parser.parse_file(json_file)

    assert len(records) == 1
    assert records[0].pid == "10.5281/zenodo.123"


def test_extract_profiles():
    """Test profile extraction from records."""
    sample_data = {
        "10.5281/zenodo.123": {
            "pid": "10.5281/zenodo.123",
            "record": [
                {
                    "key": "21.T11148/076759916209e5d62bd5",
                    "value": "21.T11969/077fe9c54ed5ed26fa54",
                },
                {
                    "key": "21.T11148/076759916209e5d62bd5",
                    "value": "21.T11969/6c663a0695a411803d70",
                },
            ],
        },
    }

    parser = FDOParser()
    records = parser.parse(sample_data)

    assert len(records[0].profiles) == 2
    assert "21.T11969/077fe9c54ed5ed26fa54" in records[0].profiles
    assert "21.T11969/6c663a0695a411803d70" in records[0].profiles


def test_get_relationships():
    """Test relationship extraction."""
    sample_data = {
        "10.5281/zenodo.123": {
            "pid": "10.5281/zenodo.123",
            "record": [
                {
                    "key": "21.T11969/7f1a6afddcfeefbf195b",
                    "value": "10.5281/zenodo.456",
                },
            ],
        },
        "10.5281/zenodo.456": {
            "pid": "10.5281/zenodo.456",
            "record": [],
        },
    }

    parser = FDOParser()
    records = parser.parse(sample_data)
    relationships = parser.get_relationships(records)

    assert len(relationships) == 1
    source, target, attr = relationships[0]
    assert source == "10.5281/zenodo.123"
    assert target == "10.5281/zenodo.456"
    assert attr.key == "21.T11969/7f1a6afddcfeefbf195b"
