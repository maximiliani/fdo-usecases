# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache2.0

"""FDO use cases package.

This package contains use case implementations for creating and consuming FDOs.
"""

from fdo_usecases.designer_lib.executor import Executor
from fdo_usecases.designs.creep.design import CreepDesign
from fdo_usecases.designs.zenodo import ZenodoFDODesign

EXECUTOR: Executor = Executor()

EXECUTOR.addDesign(ZenodoFDODesign(doi="10.5281/zenodo.20132712"))
EXECUTOR.addDesign(CreepDesign())

EXECUTOR.execute()
