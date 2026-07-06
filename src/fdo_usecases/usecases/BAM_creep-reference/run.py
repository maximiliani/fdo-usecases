#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Merge Zenodo and Creep designs into unified FDO graph."""

import asyncio
import json
import sys
from pathlib import Path

import logging

from fdo_usecases.designs.creep import CreepFDOOrchestrator
from fdo_usecases.designs.zenodo import ZenodoFDODesign
from fdo_usecases.utils.logging_config import setup_logging

from lis_parser import LISParser

async def main() -> int:
    """Main entry point with proper exit codes.
    
    Returns:
        0 on success, 1 on errors
    """
    # Setup logging
    setup_logging(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        # Step 1: Create Zenodo FDOs
        logger.info("Creating Zenodo FDOs...")
        zenodo_design = ZenodoFDODesign(dois=["10.5281/zenodo.20132712"])
        successful, failed = await zenodo_design.execute_async()
        
        if failed:
            logger.error(f"Zenodo FDO creation failed for {len(failed)} DOI(s)")
            for doi, exc in failed:
                logger.error(f"  {doi}: {type(exc).__name__}: {exc}")
            print("\n❌ Zenodo FDO creation failed.")
            return 1
        
        logger.info(f"Created Zenodo FDOs for {len(successful)} DOI(s)")
        
        # Step 2: Parse LIS files (async fetch from Zenodo)
        logger.info("Parsing LIS files...")
        async with LISParser() as lis_parser:
            lis_parser.load_from_zenodo_graph(zenodo_design._record_graph)
            
            # Step 3: Create Creep FDOs
            logger.info("Creating Creep FDOs...")
            creep_orchestrator = CreepFDOOrchestrator(zenodo_design._record_graph)
            await creep_orchestrator.execute_async(lis_parser)
            
            # Step 4: Apply inference rules
            logger.info("Applying inference rules...")
            creep_orchestrator._apply_inference_rules()
            
            # Step 5: Export unified graph
            output_path = Path(__file__).parent / "fdo_graph_merged.json"
            graph_dict = {
                k: v.toSimpleJSON() 
                for k, v in zenodo_design._record_graph.items()
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(graph_dict, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Exported {len(graph_dict)} records to {output_path}")
            
            # Step 6: Report statistics
            print("\n📊 Statistics:")
            print(f"  Total FDOs: {len(graph_dict)}")
            
            # Count by profile type
            from fdo_usecases.designs.creep.constants import (
                CREEP_EXPERIMENT_PROFILE,
                MATERIAL_PROFILE,
            )
            
            experiment_count = 0
            material_count = 0
            PROFILE_KEY = '21.T11148/076759916209e5d62bd5'
            
            for record in zenodo_design._record_graph.values():
                record_dict = record.toSimpleJSON()
                for attr in record_dict['record']:
                    if attr['key'] == PROFILE_KEY:
                        profile_value = attr['value']
                        # Handle both list and string formats
                        values = profile_value if isinstance(profile_value, list) else [profile_value]
                        
                        if CREEP_EXPERIMENT_PROFILE in values:
                            experiment_count += 1
                        if MATERIAL_PROFILE in values:
                            material_count += 1
                            
            print(f"  CreepExperiment FDOs: {experiment_count}")
            print(f"  Material FDOs: {material_count}")
            
            # Step 7: Report detailed statistics
            print("\n📊 Detailed Statistics:")
            
            # Count successful parses
            all_test_ids = set(lis_parser.group_files_by_test_id().keys())
            failed_test_ids = set(e.test_id for e in lis_parser.errors if e.test_id != "unknown")
            successful_tests = all_test_ids - failed_test_ids
            
            print(f"  Successfully parsed: {len(successful_tests)} / {len(all_test_ids)} tests")
            
            if successful_tests:
                print(f"  Test IDs: {', '.join(sorted(successful_tests))}")
            
            # Report errors with detailed information
            if lis_parser.errors:
                print(f"\n❌ LIS parsing encountered {len(lis_parser.errors)} error(s):")
                
                # Group errors by type
                from collections import Counter
                error_types = Counter(e.error_type for e in lis_parser.errors)
                
                for error_type, count in error_types.items():
                    print(f"\n  {error_type} ({count} occurrences):")
                    for error in lis_parser.errors:
                        if error.error_type == error_type:
                            print(f"    - {error.test_id}: {error.filename}")
                            print(f"      Message: {error.message}")
                
                logger.error(f"LIS parsing failed for {len(lis_parser.errors)} test(s)")
                return 1
        
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        print(f"\n❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)