# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache2.0

"""Generated design executor entry point.

This module is auto-generated and executes the configured record designs.
"""

from .executor import Executor

EXECUTOR: Executor = Executor()


EXECUTOR.execute()
