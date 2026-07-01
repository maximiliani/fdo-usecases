# FDO Graph Renderer

Interactive visualization tool for FAIR Digital Object (FDO) graphs.

## Overview

This module generates interactive HTML visualizations of FDO graphs, showing relationships between FDOs based on their attribute references. When one FDO's attribute value matches another FDO's PID, a relationship edge is created and displayed.

## Features

- **Interactive Graph Visualization**: Zoom, pan, and drag nodes using Cytoscape.js
- **Relationship Detection**: Automatically identifies relationships when FDO attributes reference other FDO PIDs
- **PID Resolution**: Resolves attribute PIDs to human-readable names via:
  - Local DTR (Digital Type Registry) JSON files
  - Network fallback via `hdl.handle.net` redirect system
- **Rich Metadata Display**: Shows all attributes, profiles, and relationship labels
- **Multiple Layout Algorithms**: Force-directed (CoSE), grid, circle, hierarchical (dagre)
- **Search & Filter**: Find nodes by PID or attribute value, filter by node type
- **Export Capabilities**: Download graph as SVG or PNG directly from browser
- **Customizable Display**: Toggle between showing PIDs, names, or both on edges

## Installation

No additional dependencies required beyond the base `fdo-usecases` project requirements.

## Usage

### CLI Command

```bash
# Basic usage
poetry run fdo-usecases-cli render-graph fdo_graph.json

# With custom output directory
poetry run fdo-usecases-cli render-graph fdo_graph.json -o ./output

# Different layout algorithm
poetry run fdo-usecases-cli render-graph fdo_graph.json --layout grid

# Offline mode (skip network resolution)
poetry run fdo-usecases-cli render-graph fdo_graph.json --offline

# Custom DTR path
poetry run fdo-usecases-cli render-graph fdo_graph.json --dtr-path ./path/to/dtr
```

### Python API

```python
from fdo_usecases.fdo_graph_renderer import generate_graph
from pathlib import Path

# Generate visualization
html_path = generate_graph(
    input_path="fdo_graph.json",
    output_dir="./fdo-graph",
    layout="cose",
    export_svg=True,
    offline=False,
    auto_detect_dtr=True
)

print(f"Generated: {html_path}")
# Open in browser to view interactive graph
```

## Module Structure

```
fdo_graph_renderer/
├── __init__.py          # Main entry point with generate_graph()
├── parser.py            # Parse FDO JSON and detect relationships
├── graph_builder.py     # Build Cytoscape.js data structures
├── pid_resolver.py      # Resolve PIDs to names/descriptions
├── renderer.py          # Generate HTML output
└── templates/
    └── graph.html       # Interactive visualization template
```

## Components

### PIDResolver

Resolves attribute PIDs to human-readable metadata:

1. **Local DTR Scan**: Loads JSON files from `info_types/`, `profiles/`, and `basic_info_types/` directories
2. **Network Fallback**: For unknown PIDs, resolves via:
   - Request to `https://hdl.handle.net/{PID}`
   - Follow redirect to type registry
   - Convert UI URL to API URL (`/#objects/` → `/objects/`)
   - Fetch JSON metadata with name and description
3. **Caching**: In-memory cache prevents duplicate lookups

```python
from fdo_usecases.fdo_graph_renderer.pid_resolver import PIDResolver

resolver = PIDResolver(dtr_path=Path("./dtr"), offline=False)
meta = resolver.resolve("21.T11969/bd3e9fb9b606d2198c9e")
# Returns: {"name": "name", "description": "...", "source": "local"}
```

### FDOParser

Parses FDO graph JSON files and identifies relationships:

```python
from fdo_usecases.fdo_graph_renderer.parser import FDOParser

parser = FDOParser(resolver=resolver)
records = parser.parse_file("fdo_graph.json")

# Get all relationships
relationships = parser.get_relationships(records)
# Returns: [(source_pid, target_pid, attribute), ...]
```

**Relationship Detection Logic:**
- For each attribute in each FDO record
- If `attribute.value` matches another FDO's PID → mark as relationship
- Creates directed edge: source FDO → target FDO

### FDOGraphBuilder

Converts parsed records to Cytoscape.js format:

```python
from fdo_usecases.fdo_graph_renderer.graph_builder import FDOGraphBuilder

builder = FDOGraphBuilder(records, resolver=resolver)
cytoscape_data = builder.to_cytoscape_format()

# Get statistics
stats = builder.get_statistics()
# Returns: {"total_nodes": N, "total_edges": M, "node_types": {...}, ...}
```

**Edge Classification:**
- **version**: nextVersion, previousVersion, latestVersion (red)
- **file**: hasData, hasMetadata, usesMaterial, etc. (green)
- **citation**: doi references (blue)
- **other**: all other relationships (gray)

### FDOGraphRenderer

Generates self-contained HTML file:

```python
from fdo_usecases.fdo_graph_renderer.renderer import FDOGraphRenderer

renderer = FDOGraphRenderer(cytoscape_data, output_dir=Path("./output"))
html_path = renderer.render(layout="cose", export_svg=True)
```

## Output Format

### Generated HTML

Single self-contained HTML file (~400KB for 164 nodes) with:

- Embedded Cytoscape.js library (loaded from CDN)
- Graph data as inline JSON
- CSS styling for controls, panels, and visualization
- JavaScript for interactivity (search, filter, export, details panel)

### Node Types

| Shape | Color | PID Pattern | Example |
|-------|-------|-------------|---------|
| Circle | Blue | `10.5281/zenodo.*` | Zenodo records |
| Rectangle | Green | `md5:.*` | File checksums |
| Diamond | Orange | `21.T.*` | Handle PIDs |
| Hexagon | Purple | Other | Unknown types |

### Relationship Types

| Color | Type | Attributes |
|-------|------|------------|
| Red | version | nextVersion, previousVersion, latestVersion |
| Green | file | hasData, hasMetadata, usesMaterial, etc. |
| Blue | citation | doi |
| Gray | other | All other relationships |

## Configuration Options

### Layout Algorithms

- **cose**: Force-directed layout with hierarchy awareness (default)
- **grid**: Nodes arranged in regular grid pattern
- **circle**: Nodes arranged in circular pattern
- **dagre**: Hierarchical top-to-bottom layout

### Display Modes

Edge labels can be toggled between:
- **PID Only**: Show full InfoType PID (e.g., `21.T11969/7f1a6afddcfeefbf195b`)
- **Name Only**: Show resolved name (e.g., `nextVersion`)
- **Combined**: Show both (default in some views)

### Filtering

- Search by PID substring or attribute value
- Filter by node type (show/hide Zenodo, MD5, Handle, Other)
- Toggle attribute descriptions in details panel

## Performance Considerations

### Recommended Limits

- **Nodes**: Up to 500 nodes performant with `cose` layout
- **Large graphs** (>500 nodes): Use `grid` or `circle` layout
- **Very large graphs** (>2000 nodes): Consider filtering or clustering

### Optimization Tips

1. Use `--offline` mode to skip network resolution for faster generation
2. Choose appropriate layout: `grid` is fastest for large graphs
3. Filter by node type to reduce complexity during exploration
4. Export static images for sharing instead of interactive HTML

## Examples

### Small Graph (10 nodes)

```bash
poetry run fdo-usecases-cli render-graph small_graph.json
```

### Medium Graph (164 nodes, Zenodo sample)

```bash
poetry run fdo-usecases-cli render-graph \
    src/fdo_usecases/designs/zenodo/fdo_graph.json \
    --layout cose
```

### Large Graph (2MB+ file)

```bash
poetry run fdo-usecases-cli render-graph \
    large_graph.json \
    --layout grid \
    --offline
```

## Testing

Run tests with pytest:

```bash
# Run all tests
poetry run pytest tests/fdo_graph_renderer/

# Run specific test file
poetry run pytest tests/fdo_graph_renderer/test_parser.py

# Run with coverage
poetry run pytest tests/fdo_graph_renderer/ --cov=fdo_usecases.fdo_graph_renderer
```

## Troubleshooting

### "Template not found" Error

Ensure the `templates/graph.html` file exists in the module directory:

```bash
ls src/fdo_usecases/fdo_graph_renderer/templates/
```

### Slow Network Resolution

If graph generation is slow due to network requests:

1. Use `--offline` flag to skip network resolution
2. Provide local DTR path with `--dtr-path`
3. Pre-populate DTR files for commonly used PIDs

### Graph Too Dense

If nodes overlap or graph is hard to read:

1. Try different layout: `--layout grid` or `--layout circle`
2. Filter by node type in the control panel
3. Zoom in and pan to explore sections
4. Use search to find specific nodes

### Missing Attribute Names

If edges show PIDs instead of names:

1. Ensure DTR files are available (auto-detected or via `--dtr-path`)
2. Check that InfoType JSON files contain `Identifier` and `name` fields
3. Network resolution will attempt to fetch missing names (unless `--offline`)

## License

Apache-2.0 (same as parent project)

## Contributing

When adding new features:

1. Add unit tests in `tests/fdo_graph_renderer/`
2. Update this README with usage examples
3. Ensure all existing tests pass: `pytest tests/fdo_graph_renderer/`
4. Test with both small and large graph files

## See Also

- [Cytoscape.js Documentation](https://js.cytoscape.org/)
- [Handle System Protocol](https://www.handle.net/hnr_doc.html)
- FDO Type Registry: https://typeregistry.lab.pidconsortium.net/
