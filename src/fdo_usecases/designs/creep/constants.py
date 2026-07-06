# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Constants for Creep FDO creation."""

# Profile Key - used to store profile PIDs in FDO records
PROFILE_KEY = "21.T11148/076759916209e5d62bd5"

# Profile PIDs
CREEP_EXPERIMENT_PROFILE = "21.T11969/222fb86c0b3bece35729"
MATERIAL_PROFILE = "21.T11969/d8169782b57c7a9e9f01"
BASE_PROFILE = "21.T11969/077fe9c54ed5ed26fa54"
VERSIONABLE_PROFILE = "21.T11969/6c663a0695a411803d70"

# InfoType PIDs
INFOTYPES = {
    # CreepExperiment specific
    "applicableStandard": "21.T11969/dda596702b20205cba36",
    "testID": "21.T11969/1a34a6966f91cc341f58",
    "specifiedTemperature": "21.T11969/ac4a911ffb09772718e3",
    "initialStress": "21.T11969/8bd53487030550ee2e94",
    "testDuration": "21.T11969/7e84faadd49ac88d02b8",
    "percentageCreepExtension": "21.T11969/4be978cac878da94105e",
    "SingleCrystalOrientation": "21.T11969/4597cf0db467d7e365a9",
    
    # Material specific
    "materialID": "21.T11969/716805eef0349802dc9a",
    "previewImage": "21.T11969/925e3f9925a88476ffba",
    "semImage": "21.T11969/19a94f596420bb274408",
    "hasChemicalComposition": "21.T11969/e32cfb93d7fc61ce3ca5",
    "hasHeatTreatment": "21.T11969/766ae14d72b49cfb5273",
    
    # Relationships
    "hasData": "21.T11969/cc230f978e8add2e2520",
    "hasMetadata": "21.T11969/d0773859091aeb451528",
    "usesMaterial": "21.T11969/2dced98076fda9cbf0ef",
    "isPartOf": "21.T11969/30f4a1f8aacab81faf38",
    "isReferencedBy": "21.T11969/e5945ef3ff07f314a146",
    "references": "21.T11969/f4c9a69f715c3c60aa2f",
    
    # Base profile
    "name": "21.T11969/bd3e9fb9b606d2198c9e",
    "description": "21.T11969/880724416f5857987e70",
    "dateCreated": "21.T11969/29f92bd203dd3eaa5a1f",
    "creator": "21.T11969/7c67083a5d218e544063",
    "creatorAffiliation": "21.T11969/ea9f6b3d78c6608fe801",
    "keyword": "21.T11969/793ff5c33c3aeb32907a",
}

# Backlink rules (forward_link_type, backward_link_type)
BACKLINK_EXPERIMENT_FILE = ("hasData", "isPartOf")
BACKLINK_MATERIAL_EXPERIMENT = ("usesMaterial", "isPartOf")
BACKLINK_MATERIAL_FILE_CHEMICAL = ("hasChemicalComposition", "isReferencedBy")
BACKLINK_MATERIAL_FILE_HEAT = ("hasHeatTreatment", "isReferencedBy")
BACKLINK_EXPERIMENT_REFERENCES_FILE = ("references", "isReferencedBy")
BACKLINK_MATERIAL_REFERENCES_FILE = ("references", "isReferencedBy")
