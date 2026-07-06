# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Material FDO design."""

import logging
from typing import TYPE_CHECKING

from fdo_usecases.designer_lib.executor import PidRecord, RecordDesign

from ..constants import (
    BACKLINK_MATERIAL_EXPERIMENT,
    BACKLINK_MATERIAL_FILE_CHEMICAL,
    BACKLINK_MATERIAL_FILE_HEAT,
    BACKLINK_MATERIAL_REFERENCES_FILE,
    BASE_PROFILE,
    INFOTYPES,
    MATERIAL_PROFILE,
    PROFILE_KEY,
)
from ..models.exchange import MaterialData

if TYPE_CHECKING:
    from ..orchestrator import CreepFDOOrchestrator

logger = logging.getLogger(__name__)


class MaterialDesign(RecordDesign):
    """Create Material FDO records.
    
    Profiles: Material + Base
    
    Each record represents one unique material composition.
    Multiple experiments can reference the same material.
    """
    
    def __init__(self, orchestrator: "CreepFDOOrchestrator | None" = None):
        super().__init__()
        self.orchestrator = orchestrator
        self._local_records: dict[str, PidRecord] = {}
        
    async def create_fdo(self, data: MaterialData) -> str:
        """Create FDO record and add to executor graph.
        
        Args:
            data: Structured material data
            
        Returns:
            Record ID (the pid_composition)
        """
        logger.info(f"Creating Material FDO for {data.material_id}")
        
        record = PidRecord()
        record.setId(data.pid_composition)
        record.setPid("")
        
        # Profiles
        record.addAttribute(
            PROFILE_KEY,
            [MATERIAL_PROFILE, BASE_PROFILE]
        )
        
        # Material attributes
        record.addAttribute(INFOTYPES["materialID"], data.material_id)
        
        # Images
        for url in data.preview_images:
            record.addAttribute(INFOTYPES["previewImage"], url)
            
        for checksum in data.sem_images:
            record.addAttribute(INFOTYPES["semImage"], checksum)
            
        # File references
        record.addAttribute(
            INFOTYPES["hasChemicalComposition"],
            data.has_chemical_composition
        )
        record.addAttribute(
            INFOTYPES["hasHeatTreatment"],
            data.has_heat_treatment
        )
        
        # Referenced files (only if no other relationship exists)
        for file_pid in data.referenced_files:
            # Check if already linked via hasChemicalComposition or hasHeatTreatment
            existing_links = [
                attr[1] for attr in record._tuples
                if attr[0] in [INFOTYPES["hasChemicalComposition"], INFOTYPES["hasHeatTreatment"]]
            ]
            if file_pid not in existing_links:
                record.addAttribute(INFOTYPES["references"], file_pid)
        
        # Base profile - Multiple descriptions allowed
        record.addAttribute(
            INFOTYPES["name"],
            f"Material {data.material_id}"
        )
        
        # Add each description as separate attribute (cardinality 0-n in practice)
        for desc in data.descriptions:
            record.addAttribute(INFOTYPES["description"], desc)
        
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
        self.addBacklink(*BACKLINK_MATERIAL_EXPERIMENT)
        self.addBacklink(*BACKLINK_MATERIAL_FILE_CHEMICAL)
        self.addBacklink(*BACKLINK_MATERIAL_FILE_HEAT)
        self.addBacklink(*BACKLINK_MATERIAL_REFERENCES_FILE)
        
        # Store in graph
        if self.orchestrator:
            self.orchestrator._record_graph[data.pid_composition] = record
            
        logger.debug(f"Created Material FDO for {data.material_id} ({data.pid_composition})")
        return data.pid_composition
