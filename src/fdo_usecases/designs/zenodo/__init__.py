# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Zenodo-specific FDO designs.

This submodule contains design definitions for Zenodo-related FDOs.

Exports:
    ZenodoFDODesign - Main orchestrator class
    ZenodoDatasetDesign - Dataset FDO creation
    ZenodoFileDesign - File FDO creation
    PublicationDesign - Publication FDO creation
"""

from fdo_usecases.designs.zenodo.designs import (
    PublicationDesign,
    ZenodoDatasetDesign,
    ZenodoFileDesign,
)
from fdo_usecases.designs.zenodo.orchestrator import ZenodoFDODesign

__all__ = [
    "ZenodoFDODesign",
    "ZenodoDatasetDesign",
    "ZenodoFileDesign",
    "PublicationDesign",
]
