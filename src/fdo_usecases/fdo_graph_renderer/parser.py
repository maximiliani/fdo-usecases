# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Parser for FDO graph JSON files.

This module parses FDO graph data and identifies relationships between FDOs.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .pid_resolver import PIDResolver


@dataclass
class FDOAttribute:
    """Represents a single attribute of an FDO."""

    key: str
    value: str
    name: str = ""
    description: str = ""
    is_relationship: bool = False


@dataclass
class FDORecord:
    """Represents a parsed FDO record."""

    pid: str
    attributes: list[FDOAttribute] = field(default_factory=list)
    profiles: list[str] = field(default_factory=list)
    node_type: str = "other"

    def get_profile_names(self, resolver: Optional[PIDResolver] = None) -> list[str]:
        """Get resolved profile names instead of PIDs."""
        if resolver is None:
            return self.profiles

        names = []
        for profile_pid in self.profiles:
            meta = resolver.resolve(profile_pid)
            names.append(meta["name"] if meta["name"] else profile_pid)
        return names


PROFILE_KEY = "21.T11148/076759916209e5d62bd5"


class FDOParser:
    """Parses FDO graph JSON files and extracts relationships."""

    def __init__(self, resolver: Optional[PIDResolver] = None):
        """Initialize parser.

        Args:
            resolver: PIDResolver instance for resolving attribute metadata.
                     If None, creates one with default settings.

        """
        self.resolver = resolver or PIDResolver()
        self.fdo_pids: set[str] = set()

    def parse_file(self, json_path: Path) -> list[FDORecord]:
        """Parse an FDO graph JSON file.

        Args:
            json_path: Path to the JSON file containing FDO graph data.

        Returns:
            List of FDORecord objects.

        """
        import json

        with open(json_path) as f:
            data = json.load(f)

        return self.parse(data)

    def parse(self, data: dict) -> list[FDORecord]:
        """Parse FDO graph data from a dictionary.

        Args:
            data: Dictionary mapping PIDs to FDO data.

        Returns:
            List of FDORecord objects.

        """
        self.fdo_pids = set(data.keys())
        records = []

        for pid, fdo_data in data.items():
            record = self._parse_fdo(pid, fdo_data)
            records.append(record)

        return records

    def _parse_fdo(self, pid: str, fdo_data: dict) -> FDORecord:
        """Parse a single FDO record.

        Args:
            pid: The FDO's persistent identifier.
            fdo_data: Dictionary containing 'record' array and 'pid' field.

        Returns:
            FDORecord object with all attributes parsed.

        """
        attributes = []
        profiles = []

        record_array = fdo_data.get("record", [])

        for attr_data in record_array:
            key = attr_data.get("key", "")
            value = attr_data.get("value", "")

            meta = self.resolver.resolve(key)

            is_rel = value in self.fdo_pids

            if key == PROFILE_KEY:
                profiles.append(value)

            attributes.append(
                FDOAttribute(
                    key=key,
                    value=value,
                    name=meta["name"],
                    description=meta["description"],
                    is_relationship=is_rel,
                )
            )

        node_type = self._classify_node(pid)

        return FDORecord(
            pid=pid, attributes=attributes, profiles=profiles, node_type=node_type
        )

    def _classify_node(self, pid: str) -> str:
        """Classify node type based on PID prefix.

        Args:
            pid: The FDO's persistent identifier.

        Returns:
            Node type string: 'zenodo', 'md5', 'handle', or 'other'.

        """
        if pid.startswith("10.5281/zenodo"):
            return "zenodo"
        elif pid.startswith("md5:"):
            return "md5"
        elif pid.startswith("21.T"):
            return "handle"
        return "other"

    def get_relationships(
        self, records: list[FDORecord]
    ) -> list[tuple[str, str, FDOAttribute]]:
        """Extract all relationships from parsed records.

        Args:
            records: List of FDORecord objects.

        Returns:
            List of tuples (source_pid, target_pid, attribute) representing edges.

        """
        relationships = []

        for record in records:
            for attr in record.attributes:
                if attr.is_relationship:
                    relationships.append((record.pid, attr.value, attr))

        return relationships
