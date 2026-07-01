# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""FDO Graph Renderer - Interactive visualization for FDO graphs.

This module generates interactive HTML visualizations of FDO (FAIR Digital Object)
graphs. All data processing, relationship detection, and PID resolution happens
client-side in the browser using the pid-component library via unpkg CDN.
"""

import logging
from pathlib import Path

from .renderer import FDOGraphRenderer

logger = logging.getLogger(__name__)


def generate_graph(
    input_path: Path | str,
    output_dir: Path | str = "./fdo-graph",
    layout: str = "cose",
    export_svg: bool = True,
) -> Path:
    """Generate an interactive FDO graph visualization.

    All graph parsing, relationship detection, and PID resolution
    happens client-side in the browser using pid-component.

    Args:
        input_path: Path to the FDO graph JSON file.
        output_dir: Directory for output files (default: ./fdo-graph).
        layout: Layout algorithm: cose, grid, circle, or dagre (default: cose).
        export_svg: Include SVG export button in HTML (default: True).

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

    renderer = FDOGraphRenderer(input_path, output_dir)
    html_path = renderer.render(layout=layout, export_svg=export_svg)

    logger.info(f"Successfully generated: {html_path}")
    return html_path


__all__ = [
    "generate_graph",
    "FDOGraphRenderer",
]
