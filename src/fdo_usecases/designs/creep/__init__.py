"""MatWerk Creep Reference Dataset-specific FDO designs."""

from fdo_usecases.designer_lib.executor import Executor
from fdo_usecases.designs.creep.design import CreepDesign

EXECUTOR: Executor = Executor()

EXECUTOR.addDesign(CreepDesign())

EXECUTOR.execute()
