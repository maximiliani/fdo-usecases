# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Renderer for FDO graph visualization.

This module generates self-contained HTML files with interactive Cytoscape.js visualizations.
"""

import json
import logging
from pathlib import Path
from typing import Union

logger = logging.getLogger(__name__)


class FDOGraphRenderer:
    """Renders FDO graphs as interactive HTML visualizations."""

    def __init__(
        self,
        graph_data: Union[dict, tuple[dict, dict]],
        output_dir: Path,
    ):
        """Initialize renderer.

        Args:
            graph_data: Cytoscape.js format graph data.
            output_dir: Directory for output files.

        """
        self.graph_data = graph_data
        self.output_dir = output_dir
        self.template_path = Path(__file__).parent / "templates" / "graph.html"

    def render(self, layout: str = "cose", export_svg: bool = True) -> Path:
        """Render the graph to an HTML file.

        Args:
            layout: Layout algorithm (cose, grid, circle, dagre).
            export_svg: Whether to include SVG export button.

        Returns:
            Path to generated HTML file.

        """
        if not self.template_path.exists():
            raise FileNotFoundError(f"Template not found: {self.template_path}")

        # Handle tuple return (graph_data, attr_defs) or dict-only for backwards compat
        graph_elements: dict
        attr_definitions: dict[str, dict[str, str]]
        if isinstance(self.graph_data, tuple):
            graph_elements, attr_definitions = self.graph_data
        else:
            graph_elements = self.graph_data
            attr_definitions = {}

        with open(self.template_path) as f:
            template_content = f.read()

        html_content = (
            template_content.replace(
                "$graph_json", json.dumps(graph_elements, separators=(",", ":"))
            )
            .replace(
                "$attr_defs_json", json.dumps(attr_definitions, separators=(",", ":"))
            )
            .replace("$layout_algorithm", layout)
            .replace("$export_svg", "true" if export_svg else "false")
        )

        self.output_dir.mkdir(parents=True, exist_ok=True)
        html_path = self.output_dir / "fdo_graph.html"

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"Generated: {html_path}")
        return html_path

    def validate_size(self, max_mb: int = 10) -> bool:
        """Validate that graph data is within size limits.

        Args:
            max_mb: Maximum recommended size in megabytes.

        Returns:
            True if within limits, False otherwise.

        """
        size_bytes = len(json.dumps(self.graph_data))
        size_mb = size_bytes / (1024 * 1024)

        if size_mb > max_mb:
            logger.warning(
                f"Graph data is {size_mb:.1f}MB (recommended: <{max_mb}MB). "
                "Consider using --layout grid for better performance."
            )
            return False
        return True
