# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Graph builder for FDO visualization.

This module converts parsed FDO records into Cytoscape.js format.
"""

from dataclasses import dataclass

from .parser import FDORecord
from .pid_resolver import PIDResolver


@dataclass
class GraphEdge:
    """Represents an edge in the FDO graph."""

    source: str
    target: str
    attribute_key: str
    attribute_name: str
    attribute_description: str
    relationship_type: str


VERSION_KEYS = {
    "21.T11969/7f1a6afddcfeefbf195b",  # nextVersion
    "21.T11969/7c97f00a2a95826c1a8f",  # previousVersion
    "21.T11969/2b4d6ceda80ddd63f7a9",  # latestVersion
}

FILE_KEYS = {
    "21.T11969/cc230f978e8add2e2520",  # hasData
    "21.T11969/d0773859091aeb451528",  # hasMetadata
    "21.T11969/2dced98076fda9cbf0ef",  # usesMaterial
    "21.T11969/766ae14d72b49cfb5273",  # hasHeatTreatment
    "21.T11969/e32cfb93d7fc61ce3ca5",  # hasChemicalComposition
    "21.T11969/19a94f596420bb274408",  # semImage
}

CITATION_KEYS = {
    "21.T11969/48e563f148dc04d8b31c",  # doi
}


class FDOGraphBuilder:
    """Builds Cytoscape.js graph data from parsed FDO records."""

    def __init__(self, records: list[FDORecord], resolver: PIDResolver | None = None):
        """Initialize graph builder.

        Args:
            records: List of parsed FDORecord objects.
            resolver: Optional PIDResolver for resolving profile names.

        """
        self.records = {r.pid: r for r in records}
        self.resolver = resolver
        self.edges: list[GraphEdge] = []
        self._build_edges()

    def _build_edges(self) -> None:
        """Build edges from relationships in FDO records."""
        for record in self.records.values():
            for attr in record.attributes:
                if attr.is_relationship:
                    edge = GraphEdge(
                        source=record.pid,
                        target=attr.value,
                        attribute_key=attr.key,
                        attribute_name=attr.name,
                        attribute_description=attr.description,
                        relationship_type=self._classify_relationship(attr.key),
                    )
                    self.edges.append(edge)

    def _classify_relationship(self, key: str) -> str:
        """Classify relationship type based on attribute key.

        Args:
            key: The InfoType PID.

        Returns:
            Relationship type: 'version', 'file', 'citation', or 'other'.

        """
        if key in VERSION_KEYS:
            return "version"
        elif key in FILE_KEYS:
            return "file"
        elif key in CITATION_KEYS:
            return "citation"
        return "other"

    def to_cytoscape_format(self) -> tuple[dict, dict]:
        """Convert graph to Cytoscape.js format.

        Returns a tuple of (graph_data, attribute_definitions) to avoid
        repeating attribute names/descriptions for every node.

        Returns:
            Tuple of (graph_elements dict, attribute_definitions dict).
            Attribute definitions map PID -> {name, description}.

        """
        elements = []
        attribute_defs: dict[str, dict] = {}

        for pid, record in self.records.items():
            profile_names = (
                record.get_profile_names(self.resolver)
                if self.resolver
                else record.profiles
            )

            # Group attributes by key and collect unique attribute definitions
            grouped_attrs: dict[str, list[str]] = {}
            for attr in record.attributes:
                if attr.key not in grouped_attrs:
                    grouped_attrs[attr.key] = []
                    # Store attribute definition once globally
                    attribute_defs[attr.key] = {
                        "name": attr.name,
                        "description": attr.description,
                    }
                grouped_attrs[attr.key].append(attr.value)

            # Store only PIDs and values, not repeated names/descriptions
            node_attributes = [
                {
                    "k": key,  # Use short keys to save space
                    "v": values if len(values) > 1 else values[0],
                    "c": len(values),
                }
                for key, values in grouped_attrs.items()
            ]

            node = {
                "data": {
                    "id": pid,
                    "label": self._truncate_pid(pid),
                    "full_pid": pid,
                    "type": record.node_type,
                    "profiles": profile_names,
                    "profile_pids": record.profiles,
                    "attrs": node_attributes,  # Short key for space efficiency
                },
                "classes": record.node_type,
            }
            elements.append(node)

        # Also deduplicate edge labels - store only key, lookup name/desc separately
        edge_elements = []
        for edge in self.edges:
            edge_elements.append(
                {
                    "data": {
                        "source": edge.source,
                        "target": edge.target,
                        "k": edge.attribute_key,  # Short key reference
                        "t": edge.relationship_type,  # Short type key
                    },
                    "classes": edge.relationship_type,
                }
            )
            # Ensure edge attribute is also in definitions
            if edge.attribute_key not in attribute_defs:
                attribute_defs[edge.attribute_key] = {
                    "name": edge.attribute_name,
                    "description": edge.attribute_description,
                }

        elements.extend(edge_elements)

        return {"elements": elements}, attribute_defs

    def _truncate_pid(self, pid: str) -> str:
        """Truncate PID for display in graph nodes.

        Args:
            pid: Full persistent identifier.

        Returns:
            Truncated PID (max 30 chars with ellipsis).

        """
        if len(pid) > 30:
            return f"{pid[:15]}...{pid[-12:]}"
        return pid

    def get_statistics(self) -> dict:
        """Get statistics about the graph.

        Returns:
            Dictionary with node counts, edge counts, and type breakdowns.

        """
        stats: dict[str, dict[str, int] | int] = {
            "total_nodes": len(self.records),
            "total_edges": len(self.edges),
            "node_types": {},
            "relationship_types": {},
        }

        for record in self.records.values():
            node_type = record.node_type
            node_types = stats["node_types"]
            if isinstance(node_types, dict):
                node_types[node_type] = node_types.get(node_type, 0) + 1

        for edge in self.edges:
            rel_type = edge.relationship_type
            rel_types = stats["relationship_types"]
            if isinstance(rel_types, dict):
                rel_types[rel_type] = rel_types.get(rel_type, 0) + 1

        return stats
