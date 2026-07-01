# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Affiliation name matching service."""

from datetime import date
from typing import Any


class AffiliationMatcher:
    """Match affiliation names to ROR IDs with timeframe validation."""

    def match(
        self,
        zenodo_affiliation: str | None,
        orcid_affiliations: list[dict[str, Any]],
        publication_date: date,
    ) -> str | None:
        """Match Zenodo affiliation string to ORCID ROR IDs.

        Compares the affiliation name from Zenodo metadata with organizations
        listed in the ORCID profile. Uses substring matching and optionally
        validates the timeframe.

        Args:
            zenodo_affiliation: Affiliation string from Zenodo metadata
            orcid_affiliations: List of affiliation records from ORCID
            publication_date: Dataset publication date for timeframe validation

        Returns:
            ROR ID URL if match found, None otherwise

        """
        if not zenodo_affiliation:
            return None

        zenodo_affil_lower = zenodo_affiliation.lower()

        for affil in orcid_affiliations:
            org_data = affil.get("organization", {})
            org_name = org_data.get("name", "")
            org_name_lower = org_name.lower()

            if not org_name:
                continue

            if (
                zenodo_affil_lower in org_name_lower
                or org_name_lower in zenodo_affil_lower
            ):
                ror_id = org_data.get("disambiguated_organization", {}).get(
                    "disambiguated_organization_identifier"
                )

                if not ror_id:
                    continue

                start_date_str = affil.get("start_date", {}).get("value")
                end_date_str = affil.get("end_date", {}).get("value")

                if start_date_str:
                    try:
                        start_year = int(start_date_str[:4])
                        if start_year > publication_date.year + 1:
                            continue
                    except ValueError:
                        pass

                if end_date_str:
                    try:
                        end_year = int(end_date_str[:4])
                        if end_year < publication_date.year - 1:
                            continue
                    except ValueError:
                        pass

                return f"https://ror.org/{ror_id}"

        return None
