# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Renderer for FDO graph visualization.

This module generates self-contained HTML files with interactive Cytoscape.js visualizations.
All data processing and PID resolution happens in the browser using the pid-component library.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class FDOGraphRenderer:
    """Renders FDO graphs as interactive HTML visualizations.

    All graph parsing, relationship detection, and PID resolution
    happens client-side in the browser using pid-component via unpkg CDN.
    """

    def __init__(self, json_path: Path, output_dir: Path):
        """Initialize renderer.

        Args:
            json_path: Path to the FDO graph JSON file (raw format).
            output_dir: Directory for output files.

        """
        self.json_path = json_path
        self.output_dir = output_dir
        self.template_path = Path(__file__).parent / "templates" / "graph.html"

        if not json_path.exists():
            raise FileNotFoundError(f"Input file not found: {json_path}")

        with open(json_path) as f:
            self.graph_data = json.load(f)

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

        with open(self.template_path) as f:
            template_content = f.read()

        html_content = (
            template_content.replace(
                "$raw_json", json.dumps(self.graph_data, separators=(",", ":"))
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
