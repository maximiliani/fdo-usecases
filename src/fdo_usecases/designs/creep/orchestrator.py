# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Creep FDO orchestrator."""

import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from fdo_usecases.designer_lib.executor import PidRecord, RecordDesign

from .constants import INFOTYPES
from .designs.experiment import CreepExperimentDesign
from .designs.material import MaterialDesign
from .models.exchange import CreepExperimentData, MaterialData

if TYPE_CHECKING:
    from ...usecases.BAM_creep_reference.lis_parser import (
        ComplementaryFiles,
        LISFileCollection,
        LISParser,
        ParsedTestMetadata,
    )

logger = logging.getLogger(__name__)


def _timedelta_to_iso8601(td: timedelta) -> str:
    """Convert timedelta to ISO 8601 duration format.
    
    Examples:
        timedelta(days=3, hours=6, minutes=42) -> "P3DT6H42M"
        timedelta(hours=2) -> "PT2H"
        timedelta(minutes=30) -> "PT30M"
    """
    days = td.days
    seconds = td.seconds
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    parts = ['P']
    if days > 0:
        parts.append(f'{days}D')
    
    if hours or minutes or secs:
        parts.append('T')
        if hours > 0:
            parts.append(f'{hours}H')
        if minutes > 0:
            parts.append(f'{minutes}M')
        if secs > 0:
            parts.append(f'{secs}S')
    
    return ''.join(parts)


class CreepFDOOrchestrator(RecordDesign):
    """Orchestrate Creep FDO creation using existing Zenodo graph.
    
    Inherits from RecordDesign to match ZenodoFDODesign pattern.
    Manages shared _record_graph for bidirectional linking.
    """
    
    def __init__(self, zenodo_graph: dict):
        super().__init__()
        self._record_graph = zenodo_graph  # Shared reference
        self.experiment_design = CreepExperimentDesign(self)
        self.material_design = MaterialDesign(self)
        self._semaphore = asyncio.Semaphore(10)
        self.INFERENCE_MATCHES_DB: dict = {}
        
    async def execute_async(self, lis_parser: "LISParser") -> None:
        """Main workflow with async concurrency.
        
        Steps:
        1. Parse LIS files (fetch from Zenodo)
        2. Identify unique materials
        3. Create Material FDOs concurrently
        4. Create CreepExperiment FDOs concurrently
        5. Apply inference rules
        """
        logger.info("Starting Creep FDO creation")
        
        # Step 1: Parse LIS files (fetch content asynchronously)
        file_collections = lis_parser.group_files_by_test_id()
        complementary_files = lis_parser.find_complementary_files()
        
        # Extract images from graph
        sem_images, preview_image_urls = lis_parser.extract_images_from_graph(self._record_graph)
        
        # Get creators/affiliations from Dataset
        dataset_creators = lis_parser.get_creators_from_dataset(self._record_graph)
        dataset_affiliations = lis_parser.get_creator_affiliations_from_dataset(self._record_graph)
        dataset_keywords = lis_parser.get_keywords_from_dataset(self._record_graph)
        
        # Step 2: Parse common metadata from MD-TR_Common-to-all.LIS
        common_metadata = await lis_parser.get_common_metadata()
        if common_metadata:
            logger.info(f"Common metadata: Material={common_metadata.material_id}, Standard={common_metadata.applicable_standard}")
        
        # Step 3: Parse each test's metadata concurrently
        test_metadata_map = {}
        
        async def parse_test(test_id: str, collection: "LISFileCollection") -> tuple[str, Optional["ParsedTestMetadata"]]:
            metadata = await lis_parser.parse_md_tr_file(collection.md_tr_checksum)
            
            # Merge with common metadata if available and fields are missing
            if metadata and common_metadata:
                if not metadata.applicable_standard and common_metadata.applicable_standard:
                    metadata.applicable_standard = common_metadata.applicable_standard
                if not metadata.material_id and common_metadata.material_id:
                    metadata.material_id = common_metadata.material_id
            
            return (test_id, metadata)
        
        parse_tasks = [parse_test(test_id, collection) for test_id, collection in file_collections.items()]
        parse_results = await asyncio.gather(*parse_tasks)
        
        for test_id, metadata in parse_results:
            if metadata:  # Skip failed parses (soft fail)
                test_metadata_map[test_id] = metadata
        
        # Step 4: Identify unique materials
        unique_materials = set(m.material_id for m in test_metadata_map.values() if m.material_id)
        logger.info(f"Found {len(unique_materials)} unique material(s)")
        
        # Step 4: Create Material FDOs concurrently
        material_tasks = []
        for material_id in unique_materials:
            # Find representative test for this material
            rep_metadata = next(
                m for m in test_metadata_map.values() 
                if m.material_id == material_id
            )
            
            # Generate PID composition
            pid_composition = f"{material_id}_{complementary_files.chemical_composition_measured}"
            
            # Extract descriptions
            descriptions = []
            if rep_metadata.manufacturing_as_manufactured:
                descriptions.append(f"As-manufactured: {rep_metadata.manufacturing_as_manufactured}")
            if rep_metadata.manufacturing_as_tested:
                descriptions.append(f"As-tested: {rep_metadata.manufacturing_as_tested}")
            
            # Extract keywords from LIS
            lis_keywords = lis_parser.extract_keywords(rep_metadata)
            keywords = lis_keywords if lis_keywords else dataset_keywords
            
            material_data = MaterialData(
                material_id=material_id,
                pid_composition=pid_composition,
                preview_images=preview_image_urls,
                sem_images=sem_images,
                has_chemical_composition=complementary_files.chemical_composition_measured,
                has_heat_treatment=complementary_files.heat_treatment,
                descriptions=descriptions,
                creators=dataset_creators,
                creator_affiliations=dataset_affiliations,
                keywords=keywords,
            )
            material_tasks.append(self.material_design.create_fdo(material_data))
            
        await asyncio.gather(*material_tasks)
        
        # Step 5: Create CreepExperiment FDOs concurrently
        experiment_tasks = []
        for test_id, metadata in test_metadata_map.items():
            collection = file_collections[test_id]
            
            # Calculate ISO 8601 duration (default PT0S if invalid)
            try:
                start = datetime.fromisoformat(metadata.date_test_start.replace(' ', 'T'))
                end = datetime.fromisoformat(metadata.date_test_end.replace(' ', 'T'))
                duration_td = end - start
                duration_iso = _timedelta_to_iso8601(duration_td)
            except (ValueError, TypeError):
                duration_iso = "PT0S"
                logger.warning(f"Invalid dates for {test_id}, using default duration PT0S")
            
            # Extract keywords from LIS
            lis_keywords = lis_parser.extract_keywords(metadata)
            keywords = lis_keywords if lis_keywords else dataset_keywords
            
            # Resolve file references
            referenced_files = []
            if hasattr(metadata, 'file_references'):
                for filename in metadata.file_references:
                    resolved_pid = await self._resolve_file_reference(filename, test_id)
                    if resolved_pid:
                        referenced_files.append(resolved_pid)
            
            experiment_data = CreepExperimentData(
                test_id=test_id,
                applicable_standard=metadata.applicable_standard,
                specified_temperature=metadata.specified_temperature,
                initial_stress=metadata.initial_stress,
                test_duration=duration_iso,
                single_crystal_orientation=metadata.single_crystal_orientation,
                percentage_creep_extension=metadata.percentage_creep_extension,
                test_job_details={
                    "dateOfTestStart": metadata.date_test_start.isoformat(),
                    "dateOfTestEnd": metadata.date_test_end.isoformat(),
                    "project": metadata.project,
                    "testID": test_id,
                },
                has_data=[
                    collection.md_tr_checksum,
                    collection.creep_checksum,
                    collection.loading_checksum,
                ],
                has_metadata=[
                    complementary_files.data_acquisition,
                    complementary_files.primary_processed_data,
                ],
                uses_material=material_id,
                creators=dataset_creators,
                creator_affiliations=dataset_affiliations,
                keywords=keywords,
                referenced_files=referenced_files,
            )
            experiment_tasks.append(self.experiment_design.create_fdo(experiment_data))
            
        await asyncio.gather(*experiment_tasks)
        
        logger.info("Creep FDO creation completed")
        
    async def _resolve_file_reference(self, filename: str, context: str) -> str | None:
        """Resolve LIS file reference to File FDO PID.
        
        Args:
            filename: Filename from LIS "See file" field
            context: Test ID or material ID for logging
            
        Returns:
            File FDO PID (checksum) if found, None otherwise
        """
        # Search _record_graph for matching File FDO
        for record_id, record in self._record_graph.items():
            # Check if this is a File FDO with matching filename
            name_attrs = [attr[1] for attr in record._tuples 
                         if attr[0] == INFOTYPES["name"]]
            if name_attrs:
                file_name = name_attrs[0].lower()
                if filename.lower() in file_name or file_name in filename.lower():
                    logger.debug(f"Resolved file reference '{filename}' to {record_id}")
                    return record_id
        
        # Log warning if not found
        logger.warning(f"File reference '{filename}' not found in graph (context: {context})")
        return None
        
    def _apply_inference_rules(self) -> None:
        """Apply backlink inference to establish bidirectional links.
        
        Copied from Executor._apply_inference_rules_to_records()
        """
        # Merge inference rules from all designs
        for design in [self.experiment_design, self.material_design]:
            if hasattr(design, '_backlinks'):
                for forward_link_type, backward_link_type in design._backlinks:
                    # Add to inference DB
                    pass  # Rules are applied automatically by RecordDesign.apply()
        
        # Apply inference
        for sender_id, sender in self._record_graph.items():
            matched_conditions = filter(
                lambda condition: sender.contains(condition),
                self.INFERENCE_MATCHES_DB.keys(),
            )
            reactions = map(
                lambda link: self.INFERENCE_MATCHES_DB[link], matched_conditions
            )
            for reaction in reactions:
                receiver: PidRecord = self._record_graph[reaction.receiver]
                receiver.addAttribute(reaction.backward_link_type, sender_id)
