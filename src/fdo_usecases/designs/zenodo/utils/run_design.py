#!/usr/bin/env python3
"""Execute Zenodo FDO design and save results to JSON.

This script runs the ZenodoFDODesign for a specific DOI and saves the resulting
FDO graph to a JSON file.

Usage:
    python -m fdo_usecases.designs.zenodo.scripts.run_design

Or modify the DOI below to process a different dataset.
"""

import json
import logging
from pathlib import Path

from fdo_usecases.designs.zenodo.orchestrator import ZenodoFDODesign
from fdo_usecases.designs.zenodo.utils.logging_config import setup_logging

if __name__ == "__main__":
    # Configure logging
    setup_logging()
    logger = logging.getLogger(__name__)

    # DOI to process (modify as needed)
    DOI = "10.5281/zenodo.20132712"

    # Execute design to create all FDOs
    logger.info(f"Starting FDO creation for DOI: {DOI}")
    design = ZenodoFDODesign(doi=DOI)
    design.execute()

    # Save FDO graph to JSON
    output_file = Path(__file__).parent.parent / "fdo_graph.json"

    graph_dict = {k: v.toSimpleJSON() for k, v in design._record_graph.items()}

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(graph_dict, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved FDO graph with {len(graph_dict)} records to {output_file}")
    print(f"Saved FDO graph with {len(graph_dict)} records to {output_file}")
