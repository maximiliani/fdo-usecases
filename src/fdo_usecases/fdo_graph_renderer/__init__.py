# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""FDO Graph Renderer - Interactive visualization for FDO graphs.

This module generates interactive HTML visualizations of FDO (FAIR Digital Object)
graphs, showing relationships between FDOs based on their attribute references.
"""

import logging
from pathlib import Path

from .graph_builder import FDOGraphBuilder
from .parser import FDOParser
from .pid_resolver import PIDResolver
from .renderer import FDOGraphRenderer

logger = logging.getLogger(__name__)


def generate_graph(
    input_path: Path | str,
    output_dir: Path | str = "./fdo-graph",
    layout: str = "cose",
    export_svg: bool = True,
    offline: bool = False,
    dtr_path: Path | str | None = None,
    auto_detect_dtr: bool = True,
) -> Path:
    """Generate an interactive FDO graph visualization.

    Args:
        input_path: Path to the FDO graph JSON file.
        output_dir: Directory for output files (default: ./fdo-graph).
        layout: Layout algorithm: cose, grid, circle, or dagre (default: cose).
        export_svg: Include SVG export button in HTML (default: True).
        offline: Skip network PID resolution (default: False).
        dtr_path: Path to DTR JSON files directory. If None and auto_detect_dtr
                 is True, attempts to find DTR files relative to input file.
        auto_detect_dtr: Automatically search for DTR files near input file
                        (default: True).

    Returns:
        Path to generated HTML file.

    Example:
        >>> from fdo_graph_renderer import generate_graph
        >>> html_path = generate_graph("fdo_graph.json")
        >>> print(f"Generated: {html_path}")

    """
    input_path = Path(input_path)
    output_dir = Path(output_dir)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    logger.info(f"Loading FDO graph from: {input_path}")

    if dtr_path is None and auto_detect_dtr:
        dtr_path = _find_dtr_path(input_path)
        if dtr_path:
            logger.info(f"Auto-detected DTR path: {dtr_path}")
        else:
            logger.info("No DTR files found, will use network resolution for PIDs")

    resolver = PIDResolver(
        dtr_path=Path(dtr_path) if dtr_path else None, offline=offline
    )

    parser = FDOParser(resolver=resolver)
    records = parser.parse_file(input_path)

    logger.info(f"Parsed {len(records)} FDO records")

    builder = FDOGraphBuilder(records, resolver=resolver)
    graph_data, attr_defs = builder.to_cytoscape_format()

    stats = builder.get_statistics()
    logger.info(
        f"Graph statistics: {stats['total_nodes']} nodes, {stats['total_edges']} edges"
    )
    logger.info(f"Node types: {stats['node_types']}")
    logger.info(f"Relationship types: {stats['relationship_types']}")

    renderer = FDOGraphRenderer((graph_data, attr_defs), output_dir)
    renderer.validate_size(max_mb=10)

    html_path = renderer.render(layout=layout, export_svg=export_svg)

    logger.info(f"Successfully generated: {html_path}")
    return html_path


def _find_dtr_path(input_path: Path) -> Path | None:
    """Attempt to find DTR files relative to input file location.

    Searches in parent directories for a 'dtr' folder containing InfoType JSON files.

    Args:
        input_path: Path to the input FDO graph JSON file.

    Returns:
        Path to DTR directory if found, None otherwise.

    """
    current = input_path.parent.absolute()

    while current != current.parent:
        dtr_candidate = current / "dtr"
        if dtr_candidate.exists():
            info_types = dtr_candidate / "info_types"
            if info_types.exists() and any(info_types.glob("*.json")):
                return dtr_candidate

        current = current.parent

    project_root = input_path.parent.parent.parent
    dtr_path = project_root / "usecases" / "BAM_creep-reference" / "dtr"
    if dtr_path.exists() and (dtr_path / "info_types").exists():
        return dtr_path

    return None


__all__ = [
    "generate_graph",
    "FDOParser",
    "FDOGraphBuilder",
    "PIDResolver",
    "FDOGraphRenderer",
]
