# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for FDO graph builder."""

from fdo_usecases.fdo_graph_renderer.graph_builder import (
    FDOGraphBuilder,
)
from fdo_usecases.fdo_graph_renderer.parser import FDOAttribute, FDORecord


def test_build_edges_from_relationships():
    """Test that edges are built from relationships."""
    records = [
        FDORecord(
            pid="10.5281/zenodo.123",
            attributes=[
                FDOAttribute(
                    key="21.T11969/7f1a6afddcfeefbf195b",
                    value="10.5281/zenodo.456",
                    name="nextVersion",
                    is_relationship=True,
                )
            ],
            node_type="zenodo",
        ),
        FDORecord(
            pid="10.5281/zenodo.456",
            attributes=[],
            node_type="zenodo",
        ),
    ]

    builder = FDOGraphBuilder(records)

    assert len(builder.edges) == 1
    edge = builder.edges[0]
    assert edge.source == "10.5281/zenodo.123"
    assert edge.target == "10.5281/zenodo.456"
    assert edge.attribute_name == "nextVersion"


def test_classify_version_edges():
    """Test version relationship classification."""
    records = [
        FDORecord(
            pid="10.5281/zenodo.123",
            attributes=[
                FDOAttribute(
                    key="21.T11969/7f1a6afddcfeefbf195b",
                    value="10.5281/zenodo.456",
                    is_relationship=True,
                )
            ],
            node_type="zenodo",
        ),
        FDORecord(pid="10.5281/zenodo.456", attributes=[], node_type="zenodo"),
    ]

    builder = FDOGraphBuilder(records)

    assert len(builder.edges) == 1
    assert builder.edges[0].relationship_type == "version"


def test_classify_file_edges():
    """Test file relationship classification."""
    records = [
        FDORecord(
            pid="10.5281/zenodo.123",
            attributes=[
                FDOAttribute(
                    key="21.T11969/cc230f978e8add2e2520",
                    value="md5:abc123",
                    is_relationship=True,
                )
            ],
            node_type="zenodo",
        ),
        FDORecord(pid="md5:abc123", attributes=[], node_type="md5"),
    ]

    builder = FDOGraphBuilder(records)

    assert len(builder.edges) == 1
    assert builder.edges[0].relationship_type == "file"


def test_to_cytoscape_format():
    """Test conversion to Cytoscape.js format."""
    records = [
        FDORecord(
            pid="10.5281/zenodo.123",
            attributes=[
                FDOAttribute(
                    key="21.T11969/bd3e9fb9b606d2198c9e",
                    value="Test Dataset",
                    name="name",
                    is_relationship=False,
                )
            ],
            profiles=["21.T11969/077fe9c54ed5ed26fa54"],
            node_type="zenodo",
        ),
    ]

    builder = FDOGraphBuilder(records)
    data, attr_defs = builder.to_cytoscape_format()

    assert "elements" in data
    assert len(data["elements"]) == 1

    # Check attribute definitions are separate
    assert "21.T11969/bd3e9fb9b606d2198c9e" in attr_defs
    assert attr_defs["21.T11969/bd3e9fb9b606d2198c9e"]["name"] == "name"

    node = data["elements"][0]
    assert node["data"]["id"] == "10.5281/zenodo.123"
    assert node["data"]["type"] == "zenodo"
    assert len(node["data"]["attrs"]) == 1
    assert node["data"]["attrs"][0]["k"] == "21.T11969/bd3e9fb9b606d2198c9e"


def test_truncate_long_pids():
    """Test PID truncation for display."""
    records = [
        FDORecord(
            pid="10.5281/zenodo.verylongidentifierthatexceedsthirtycharacters",
            attributes=[],
            node_type="zenodo",
        ),
    ]

    builder = FDOGraphBuilder(records)
    data, attr_defs = builder.to_cytoscape_format()

    node = data["elements"][0]
    assert "..." in node["data"]["label"]
    assert len(node["data"]["label"]) <= 30


def test_get_statistics():
    """Test graph statistics calculation."""
    records = [
        FDORecord(
            pid="10.5281/zenodo.123",
            attributes=[
                FDOAttribute(key="k", value="10.5281/zenodo.456", is_relationship=True)
            ],
            node_type="zenodo",
        ),
        FDORecord(pid="10.5281/zenodo.456", attributes=[], node_type="zenodo"),
        FDORecord(pid="md5:abc", attributes=[], node_type="md5"),
    ]

    builder = FDOGraphBuilder(records)
    stats = builder.get_statistics()

    assert stats["total_nodes"] == 3
    assert stats["total_edges"] == 1
    assert stats["node_types"]["zenodo"] == 2
    assert stats["node_types"]["md5"] == 1


def test_multiple_edges_between_nodes():
    """Test multiple relationships between same nodes."""
    records = [
        FDORecord(
            pid="10.5281/zenodo.123",
            attributes=[
                FDOAttribute(
                    key="21.T11969/7f1a6afddcfeefbf195b",
                    value="10.5281/zenodo.456",
                    name="nextVersion",
                    is_relationship=True,
                ),
                FDOAttribute(
                    key="21.T11969/7c97f00a2a95826c1a8f",
                    value="10.5281/zenodo.456",
                    name="previousVersion",
                    is_relationship=True,
                ),
            ],
            node_type="zenodo",
        ),
        FDORecord(pid="10.5281/zenodo.456", attributes=[], node_type="zenodo"),
    ]

    builder = FDOGraphBuilder(records)

    assert len(builder.edges) == 2
    assert all(e.source == "10.5281/zenodo.123" for e in builder.edges)
    assert all(e.target == "10.5281/zenodo.456" for e in builder.edges)
    assert builder.edges[0].attribute_name == "nextVersion"
    assert builder.edges[1].attribute_name == "previousVersion"
