# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Sub-designs for Zenodo FDO creation."""

from fdo_usecases.designs.zenodo.designs.dataset import ZenodoDatasetDesign
from fdo_usecases.designs.zenodo.designs.file import ZenodoFileDesign
from fdo_usecases.designs.zenodo.designs.publication import PublicationDesign

__all__ = [
    "ZenodoDatasetDesign",
    "ZenodoFileDesign",
    "PublicationDesign",
]
