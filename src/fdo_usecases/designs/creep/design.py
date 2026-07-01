# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Creep data design module."""

from fdo_usecases.designer_lib.executor import RecordDesign


class CreepDesign(RecordDesign):
    """Creep data record design."""

    def __init__(self):
        """Initialize creep design."""
        super().__init__()
