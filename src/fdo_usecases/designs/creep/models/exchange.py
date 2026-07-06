# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Exchange models for Creep FDO creation."""

from dataclasses import dataclass, field


@dataclass
class CreepExperimentData:
    """Complete data needed to create a CreepExperiment FDO record.
    
    Attributes:
        test_id: Unique test identifier (e.g., "Vh5205_C-78")
        applicable_standard: Test standard (e.g., "DIN EN ISO 204:2019-4")
        specified_temperature: Test temperature in °C
        initial_stress: Applied stress in MPa
        test_duration: ISO 8601 duration string (e.g., "P3DT6H42M")
        single_crystal_orientation: Crystal angle in degrees [0-360]
        test_job_details: Dict with dateOfTestStart, dateOfTestEnd, project, testID
        has_data: List of file checksums (MD-TR, Creep, Loading LIS files)
        has_metadata: List of complementary file checksums
        uses_material: Material ID reference (e.g., "CMSX-6")
        percentage_creep_extension: Creep strain as ratio 0-1 (default: 0.0)
        creators: Combined creator ORCIDs from Dataset
        creator_affiliations: Combined ROR IDs from Dataset
        keywords: Domain-specific keywords or inherited from Dataset
        referenced_files: List of resolved File FDO PIDs from "See file" references
    """
    test_id: str
    applicable_standard: str
    specified_temperature: float
    initial_stress: float
    test_duration: str  # ISO 8601
    single_crystal_orientation: float
    test_job_details: dict
    has_data: list[str]
    has_metadata: list[str]
    uses_material: str
    percentage_creep_extension: float = 0.0
    creators: list[str] = field(default_factory=list)
    creator_affiliations: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    referenced_files: list[str] = field(default_factory=list)


@dataclass
class MaterialData:
    """Complete data needed to create a Material FDO record.
    
    Attributes:
        material_id: Unique material identifier (e.g., "CMSX-6")
        pid_composition: Composite PID: material_id + chemical composition FDO handle
        has_chemical_composition: Checksum to chemical composition LIS file (File FDO PID)
        has_heat_treatment: Checksum to heat treatment LIS file (File FDO PID)
        descriptions: List of description strings (as-manufactured, as-tested, etc.)
        preview_images: List of URLs to .jpg images
        sem_images: List of checksums to .tiff SEM images
        creators: Combined creator ORCIDs from Dataset
        creator_affiliations: Combined ROR IDs from Dataset
        keywords: Domain-specific keywords or inherited from Dataset
        referenced_files: List of resolved File FDO PIDs from "See file" references
    """
    material_id: str
    pid_composition: str
    has_chemical_composition: str
    has_heat_treatment: str
    descriptions: list[str] = field(default_factory=list)
    preview_images: list[str] = field(default_factory=list)
    sem_images: list[str] = field(default_factory=list)
    creators: list[str] = field(default_factory=list)
    creator_affiliations: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    referenced_files: list[str] = field(default_factory=list)
