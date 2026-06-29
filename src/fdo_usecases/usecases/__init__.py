"""FDO use cases package.

This package contains use case implementations for creating and consuming FDOs.
"""

from fdo_usecases.designer_lib.executor import Executor
from fdo_usecases.designs.creep.design import CreepDesign
from fdo_usecases.designs.zenodo import ZenodoDesign

EXECUTOR: Executor = Executor()

EXECUTOR.addDesign(ZenodoDesign(doi="10.5281/zenodo.20132712"))
EXECUTOR.addDesign(CreepDesign())

EXECUTOR.execute()
