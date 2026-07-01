# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache2.0

"""ROR ID enrichment service."""

from datetime import date
from typing import Any

from fdo_usecases.designs.zenodo.api_clients import (
    OrcidApiClient,
    ZenodoExportApiClient,
)
from fdo_usecases.designs.zenodo.enrichment.affiliation_matcher import (
    AffiliationMatcher,
)
from fdo_usecases.designs.zenodo.models import Creator, Dataset


class ROREnricher:
    """Enrich creators with ROR IDs (priority: Zenodo export > ORCID)."""

    def __init__(
        self,
        export_client: ZenodoExportApiClient,
        orcid_client: OrcidApiClient,
    ):
        """Initialize ROR enricher with API clients.

        Args:
            export_client: Zenodo export API client for structured metadata
            orcid_client: ORCID API client for researcher profiles

        """
        self.export_client = export_client
        self.orcid_client = orcid_client
        self.affiliation_matcher = AffiliationMatcher()

    async def enrich(self, record_data: dict[str, Any], dataset: Dataset) -> None:
        """Enrich all creators in all versions with ROR IDs.

        Priority order:
        1. Extract ROR IDs from Zenodo export metadata (structured affiliations)
        2. Match Zenodo free-text affiliation + ORCID resolved ROR
        3. Skip if no ROR found

        Args:
            record_data: Original record data from Zenodo API
            dataset: Dataset object with creators to enrich (modified in-place)

        """
        export_data = await self._fetch_export(record_data["id"])

        for version in dataset.versions.values():
            for creator in version.creators:
                ror_id = await self._get_ror_id(
                    export_data, creator, version.publication_date
                )
                if ror_id:
                    creator.ror_id = ror_id

    async def _fetch_export(self, recid: int) -> dict[str, Any] | None:
        """Fetch Zenodo export JSON.

        Args:
            recid: Zenodo record ID

        Returns:
            Export data dictionary or None if fetch failed

        """
        try:
            async with self.export_client:
                return await self.export_client.get_record_export(recid)
        except Exception:
            return None

    async def _get_ror_id(
        self,
        export_data: dict[str, Any] | None,
        creator: Creator,
        publication_date: date,
    ) -> str | None:
        """Get ROR ID with priority: Zenodo export > ORCID profile.

        Args:
            export_data: Zenodo export JSON (or None)
            creator: Creator object to find ROR for
            publication_date: Dataset publication date for timeframe validation

        Returns:
            ROR ID URL if found, None otherwise

        """
        # Priority 1: Extract from Zenodo export
        ror_id = self._extract_from_export(export_data, creator)

        # Priority 2: ORCID profile lookup
        if not ror_id and creator.orcid:
            try:
                employments = await self.orcid_client.get_employments(creator.orcid)
                educations = await self.orcid_client.get_educations(creator.orcid)

                matched_ror = self.affiliation_matcher.match(
                    creator.affiliation,
                    employments + educations,
                    publication_date,
                )

                if matched_ror:
                    ror_id = matched_ror

            except Exception:
                pass

        return ror_id

    def _extract_from_export(
        self,
        export_data: dict[str, Any] | None,
        creator: Creator,
    ) -> str | None:
        """Extract ROR ID from Zenodo export JSON structured affiliations.

        Parses the export JSON format where creators have structured
        affiliations array with identifiers:
        {
          "affiliations": [{
            "identifiers": [
              {"identifier": "03x516a66", "scheme": "ror"},
              ...
            ]
          }]
        }

        Matches creators by name and ORCID between export data and
        existing creator object.

        Args:
            export_data: Complete export JSON from Zenodo (or None if fetch failed)
            creator: Creator object to find ROR for

        Returns:
            ROR ID URL if found, None otherwise

        """
        if not export_data:
            return None

        export_creators = export_data.get("metadata", {}).get("creators", [])

        creator_name = creator.name.strip().lower()
        creator_orcid = creator.orcid

        for exp_creator in export_creators:
            person_or_org = exp_creator.get("person_or_org", {})
            exp_name = person_or_org.get("name", "").strip().lower()
            exp_identifiers = person_or_org.get("identifiers", [])

            name_match = creator_name == exp_name or creator_name in exp_name

            orcid_match = False
            if creator_orcid:
                for ident in exp_identifiers:
                    if (
                        ident.get("scheme") == "orcid"
                        and ident.get("identifier") == creator_orcid
                    ):
                        orcid_match = True
                        break

            if not (name_match or orcid_match):
                continue

            affiliations = exp_creator.get("affiliations", [])
            for affil in affiliations:
                identifiers = affil.get("identifiers", [])
                for ident in identifiers:
                    if ident.get("scheme") == "ror":
                        ror_id_value = ident.get("identifier")
                        if ror_id_value:
                            return f"https://ror.org/{ror_id_value}"

        return None
