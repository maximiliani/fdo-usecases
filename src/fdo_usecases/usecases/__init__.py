# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""FDO use cases package.

This package contains use case implementations for creating and consuming FDOs.
"""

import os

from dotenv import load_dotenv

# Load configuration from .env before reading any environment variables.
# This must happen before the SKIP_EXECUTOR check below, which is evaluated
# during import, and before run.py reads the FDO_ES_* / FDO_TPM_* settings.
load_dotenv()

# Skip executor during testing
if os.environ.get("SKIP_EXECUTOR") != "1":
    from fdo_usecases.designer_lib.executor import Executor
    from fdo_usecases.designs.creep.design import CreepDesign
    from fdo_usecases.designs.zenodo import ZenodoFDODesign

    EXECUTOR: Executor = Executor()

    EXECUTOR.addDesign(ZenodoFDODesign(dois=["10.5281/zenodo.20132712"]))
    EXECUTOR.addDesign(CreepDesign())

    EXECUTOR.execute()
