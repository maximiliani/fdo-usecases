#!/usr/bin/env python3
"""Execute Zenodo FDO design and save results to JSON.

This script runs the ZenodoFDODesign for multiple DOIs in parallel and saves
the resulting FDO graph to a JSON file.

Usage:
    python -m fdo_usecases.designs.zenodo.scripts.run_design

Modify the DOIS list and MAX_CONCURRENT below to customize execution.
"""

import asyncio
import json
import logging
from pathlib import Path

from fdo_usecases.designs.zenodo.orchestrator import ZenodoFDODesign
from fdo_usecases.utils.logging_config import setup_logging

if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger(__name__)

    # ===== CONFIGURATION =====
    DOIS = [
        "10.5281/zenodo.20132712",
    ]
    MAX_CONCURRENT = 10
    # =========================

    logger.info(f"Starting FDO creation for {len(DOIS)} DOI(s)")
    design = ZenodoFDODesign(dois=DOIS, max_concurrent=MAX_CONCURRENT)
    successful, failed = asyncio.run(design.execute_async())

    output_file = Path(__file__).parent.parent / "fdo_graph.json"
    graph_dict = {k: v.toSimpleJSON() for k, v in design._record_graph.items()}

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(graph_dict, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved FDO graph with {len(graph_dict)} records to {output_file}")
    print(f"\n✅ Successful: {len(successful)} DOI(s)")
    if failed:
        print(f"❌ Failed: {len(failed)} DOI(s)")
    print(f"📊 Total records created: {len(graph_dict)}")
    print(f"💾 Saved to: {output_file}")
