# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""CLI of fdo-usecases."""

from pathlib import Path

import typer

# create subcommand app
say = typer.Typer()

# create main app
app = typer.Typer()
app.add_typer(say, name="say")


@app.command("render-graph")
def render_graph(
    input_path: Path = typer.Argument(..., help="Path to FDO graph JSON file"),
    output_dir: Path = typer.Option(
        "./fdo-graph", "-o", "--output-dir", help="Output directory"
    ),
    layout: str = typer.Option(
        "cose",
        "-l",
        "--layout",
        help="Layout algorithm: cose, grid, circle, dagre",
    ),
) -> None:
    """Render an FDO graph as an interactive HTML visualization.

    PID resolution happens in the browser via handle.net API.
    Internet connection required when opening the HTML file.
    """
    from fdo_usecases.fdo_graph_renderer import generate_graph

    html_path = generate_graph(
        input_path=input_path,
        output_dir=output_dir,
        layout=layout,
        export_svg=True,
    )
    print(f"✓ Generated: {html_path}")
    print("  Open this file in a browser to view the interactive graph")
    print("  (Internet connection required for PID resolution)")
