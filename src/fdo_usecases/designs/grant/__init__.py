# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Reusable Grant FDO design for creating Grant FDO records.

This module provides tools for creating Grant FDOs with validated funder identifiers
(ROR IDs and CrossRef Funder DOIs), managing grant metadata, and establishing
funding relationships between grants and research outputs.

Components:
    - grant_design: Main design class for creating Grant FDO records
    - registry: Static grant registry with pre-registered grants
    - crossref_funder: HTTP client for CrossRef Funder Registry API
    - ror: HTTP client for ROR API
    - validator: Funder ID validation utilities

Example:
    ```python
    from fdo_usecases.designs.grant import GrantDesign, GrantRegistryEntry

    # Create a grant design
    graph = {}
    design = GrantDesign(graph)

    # Create grant data
    from fdo_usecases.designs.zenodo.models.exchange import GrantFDOData
    data = GrantFDOData(
        funder_ror_id="https://ror.org/018mejw64",
        funder_name="Deutsche Forschungsgemeinschaft",
        grant_code="460247524",
        project_name="NFDI-MatWerk",
        project_website="https://nfdi-matwerk.de"
    )

    # Create the Grant FDO
    grant_id = await design.create_fdo(data)
    ```

For more information, see the README.md in this directory.

"""

from fdo_usecases.designs.grant.crossref_funder import CrossrefFunderApiClient
from fdo_usecases.designs.grant.grant_design import GRANT_PROFILE_PID, GrantDesign
from fdo_usecases.designs.grant.registry import (
    PRE_REGISTERED_GRANTS,
    GrantRegistryEntry,
)
from fdo_usecases.designs.grant.ror import RorApiClient
from fdo_usecases.designs.grant.validator import FunderIDValidator

__all__ = [
    # Main design
    "GrantDesign",
    "GRANT_PROFILE_PID",
    # Registry
    "GrantRegistryEntry",
    "PRE_REGISTERED_GRANTS",
    # API clients
    "CrossrefFunderApiClient",
    "RorApiClient",
    # Validator
    "FunderIDValidator",
]
