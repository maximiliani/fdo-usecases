# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Static grant registry for pre-registered grants with authoritative information.

This module provides a registry of pre-defined grants that take precedence
over automatically extracted grant data from sources like Zenodo. This is
useful for ensuring consistent, authoritative information for well-known
grants and projects.

Example:
    ```python
    from fdo_usecases.designs.grant import PRE_REGISTERED_GRANTS

    # Access MatWerk grant
    matwerk = PRE_REGISTERED_GRANTS["matwerk"]
    print(matwerk.funder_name)  # "Deutsche Forschungsgemeinschaft"
    print(matwerk.unique_key)   # "https://ror.org/018mejw64::460247524"

    # Check if a grant is pre-registered
    key = "https://ror.org/018mejw64::460247524"
    if key in [entry.unique_key for entry in PRE_REGISTERED_GRANTS.values()]:
        print("Grant is pre-registered")
    ```

"""

from dataclasses import dataclass


@dataclass(frozen=True)
class GrantRegistryEntry:
    """Pre-registered grant with authoritative information.

    Represents a grant entry in the static registry with verified,
    authoritative information that overrides automatically extracted data.

    Attributes:
        funder_name: Human-readable name of the funding organization
            (e.g., "Deutsche Forschungsgemeinschaft")
        grant_code: Grant award number or code assigned by the funder
            (e.g., "460247524", "Po 405/2-1")
        funder_ror_id: ROR identifier URL for the funding organization
            (e.g., "https://ror.org/018mejw64"). Optional but recommended.
        funder_crossref_doi: CrossRef Funder Registry DOI for the funding
            organization (e.g., "https://doi.org/10.13039/501100001659").
            Optional, can be used alongside or instead of ROR ID.
        project_name: Official title of the funded research project
            (e.g., "NFDI-MatWerk"). Optional.
        project_website: URL to the project's official website or landing
            page (e.g., "https://nfdi-matwerk.de"). Optional.

    Example:
        ```python
        entry = GrantRegistryEntry(
            funder_name="Deutsche Forschungsgemeinschaft",
            grant_code="460247524",
            funder_ror_id="https://ror.org/018mejw64",
            funder_crossref_doi="https://doi.org/10.13039/501100001659",
            project_name="NFDI-MatWerk",
            project_website="https://nfdi-matwerk.de"
        )
        print(entry.unique_key)  # "https://ror.org/018mejw64::460247524"
        ```

    """

    funder_name: str
    grant_code: str
    funder_ror_id: str | None = None
    funder_crossref_doi: str | None = None
    project_name: str | None = None
    project_website: str | None = None

    @property
    def unique_key(self) -> str:
        """Generate unique identifier for deduplication.

        Creates a composite key from the funder ID (ROR or CrossRef DOI)
        and grant code. This key is used to match pre-registered grants
        with automatically extracted grant data.

        Returns:
            Unique key string in format: `<funder_id>::<grant_code>`
            where funder_id is the ROR ID if available, otherwise CrossRef DOI.

        Example:
            >>> entry = GrantRegistryEntry(
            ...     funder_name="DFG",
            ...     grant_code="460247524",
            ...     funder_ror_id="https://ror.org/018mejw64"
            ... )
            >>> entry.unique_key
            'https://ror.org/018mejw64::460247524'

        """
        funder_id = self.funder_ror_id or self.funder_crossref_doi
        return f"{funder_id}::{self.grant_code}"


# Pre-registered grants (static, authoritative)
# These take precedence over Zenodo-extracted grant data
PRE_REGISTERED_GRANTS: dict[str, GrantRegistryEntry] = {
    "matwerk": GrantRegistryEntry(
        funder_ror_id="https://ror.org/018mejw64",  # DFG
        funder_crossref_doi="https://doi.org/10.13039/501100001659",
        funder_name="Deutsche Forschungsgemeinschaft",
        grant_code="460247524",
        project_name="NFDI-MatWerk",
        project_website="https://nfdi-matwerk.de",
    ),
    # Add more pre-registered grants here
    # Example:
    # "example_grant": GrantRegistryEntry(
    #     funder_name="Example Foundation",
    #     grant_code="EX-12345",
    #     funder_ror_id="https://ror.org/xxxxxxxxx",
    #     project_name="Example Project",
    #     project_website="https://example.org"
    # ),
}


__all__ = ["GrantRegistryEntry", "PRE_REGISTERED_GRANTS"]
