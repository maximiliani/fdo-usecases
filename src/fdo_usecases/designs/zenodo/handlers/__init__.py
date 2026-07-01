# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache2.0

"""Reference processing handlers."""

from fdo_usecases.designs.zenodo.handlers.publication_handler import (
    PublicationReferenceHandler,
)
from fdo_usecases.designs.zenodo.handlers.reference_processor import (
    ReferenceHandler,
    ReferenceProcessor,
)
from fdo_usecases.designs.zenodo.handlers.zenodo_handler import ZenodoReferenceHandler

__all__ = [
    "ReferenceHandler",
    "ReferenceProcessor",
    "ZenodoReferenceHandler",
    "PublicationReferenceHandler",
]
