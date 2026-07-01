# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache2.0

"""MatWerk Creep Reference Dataset-specific FDO designs."""

from fdo_usecases.designer_lib.executor import Executor
from fdo_usecases.designs.creep.design import CreepDesign

EXECUTOR: Executor = Executor()

EXECUTOR.addDesign(CreepDesign())

EXECUTOR.execute()
