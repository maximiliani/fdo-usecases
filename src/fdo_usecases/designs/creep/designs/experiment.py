# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""CreepExperiment FDO design."""

import logging
from typing import TYPE_CHECKING

from fdo_usecases.designer_lib.executor import PidRecord, RecordDesign

from ..constants import (
    BACKLINK_EXPERIMENT_FILE,
    BACKLINK_EXPERIMENT_REFERENCES_FILE,
    BACKLINK_MATERIAL_EXPERIMENT,
    BASE_PROFILE,
    CREEP_EXPERIMENT_PROFILE,
    INFOTYPES,
    PROFILE_KEY,
    VERSIONABLE_PROFILE,
)
from ..models.exchange import CreepExperimentData

if TYPE_CHECKING:
    from ..orchestrator import CreepFDOOrchestrator

logger = logging.getLogger(__name__)


class CreepExperimentDesign(RecordDesign):
    """Create CreepExperiment FDO records.
    
    Profiles: CreepExperiment + Base + Versionable
    
    Each record represents one creep test with:
    - Test parameters (temperature, stress, duration)
    - Relationships to files (hasData, hasMetadata)
    - Relationship to material (usesMaterial)
    """
    
    def __init__(self, orchestrator: "CreepFDOOrchestrator | None" = None):
        super().__init__()
        self.orchestrator = orchestrator
        self._local_records: dict[str, PidRecord] = {}
        
    async def create_fdo(self, data: CreepExperimentData) -> str:
        """Create FDO record and add to executor graph.
        
        Args:
            data: Structured experiment data
            
        Returns:
            Record ID (the test_id)
        """
        logger.info(f"Creating CreepExperiment FDO for {data.test_id}")
        
        record = PidRecord()
        record.setId(data.test_id)
        record.setPid("")
        
        # Profiles
        record.addAttribute(
            PROFILE_KEY,
            [CREEP_EXPERIMENT_PROFILE, BASE_PROFILE, VERSIONABLE_PROFILE]
        )
        
        # CreepExperiment attributes
        record.addAttribute(INFOTYPES["applicableStandard"], data.applicable_standard)
        record.addAttribute(INFOTYPES["testID"], data.test_id)
        record.addAttribute(INFOTYPES["specifiedTemperature"], data.specified_temperature)
        record.addAttribute(INFOTYPES["initialStress"], data.initial_stress)
        record.addAttribute(INFOTYPES["testDuration"], data.test_duration)
        
        # Only add if non-zero (soft fail for missing data)
        if data.percentage_creep_extension > 0:
            record.addAttribute(
                INFOTYPES["percentageCreepExtension"],
                data.percentage_creep_extension
            )
            
        # Only add if non-zero (soft fail for missing data)
        if data.single_crystal_orientation > 0:
            record.addAttribute(
                INFOTYPES["SingleCrystalOrientation"],
                data.single_crystal_orientation
            )
        
        # Relationships - Files
        for checksum in data.has_data:
            record.addAttribute(INFOTYPES["hasData"], checksum)
            
        for checksum in data.has_metadata:
            record.addAttribute(INFOTYPES["hasMetadata"], checksum)
            
        # Relationship - Material
        record.addAttribute(INFOTYPES["usesMaterial"], data.uses_material)
        
        # Referenced files (only if no other relationship exists)
        for file_pid in data.referenced_files:
            # Check if already linked via hasData or hasMetadata
            existing_links = [
                attr[1] for attr in record._tuples
                if attr[0] in [INFOTYPES["hasData"], INFOTYPES["hasMetadata"]]
            ]
            if file_pid not in existing_links:
                record.addAttribute(INFOTYPES["references"], file_pid)
        
        # Base profile attributes
        record.addAttribute(
            INFOTYPES["name"],
            f"Creep Test {data.test_id}"
        )
        record.addAttribute(
            INFOTYPES["dateCreated"],
            data.test_job_details["dateOfTestStart"]
        )
        
        # Description
        description = f"Creep test at {data.specified_temperature}°C, {data.initial_stress} MPa"
        record.addAttribute(INFOTYPES["description"], description)
        
        # Creators (combined from Dataset)
        if data.creators:
            record.addAttribute(INFOTYPES["creator"], data.creators)
            
        # Creator affiliations (combined from Dataset)
        if data.creator_affiliations:
            record.addAttribute(INFOTYPES["creatorAffiliation"], data.creator_affiliations)
        
        # Keywords
        if data.keywords:
            record.addAttribute(INFOTYPES["keyword"], data.keywords)
        
        # Backlinks for inference
        self.addBacklink(*BACKLINK_EXPERIMENT_FILE)
        self.addBacklink(*BACKLINK_MATERIAL_EXPERIMENT)
        self.addBacklink(*BACKLINK_EXPERIMENT_REFERENCES_FILE)
        
        # Store in graph
        self._local_records[data.test_id] = record
        if self.orchestrator:
            self.orchestrator._record_graph[data.test_id] = record
            
        logger.debug(f"Created CreepExperiment FDO for {data.test_id}")
        return data.test_id
