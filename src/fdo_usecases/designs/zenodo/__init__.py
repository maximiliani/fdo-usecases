"""Zenodo-specific FDO designs.

This submodule contains design definitions for Zenodo-related FDOs.
"""

from fdo_usecases.designer_lib.executor import Executor
from fdo_usecases.designs.zenodo.design import ZenodoDesign

EXECUTOR: Executor = Executor()

EXECUTOR.addDesign(ZenodoDesign(doi="10.5281/zenodo.20132712"))

EXECUTOR.execute()
