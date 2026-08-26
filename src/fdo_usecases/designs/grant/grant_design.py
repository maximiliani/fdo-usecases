# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Grant FDO design implementation.

This module provides the GrantDesign class for creating Grant FDO records
with validated funder identifiers and proper metadata structure.

"""

import logging
import re

from fdo_usecases.designer_lib.executor import PidRecord, RecordDesign

logger = logging.getLogger(__name__)

# Grant profile PID
GRANT_PROFILE_PID = "21.T11969/c02329c48f348eb63368"

# Profile key for storing profile PIDs
PROFILE_KEY = "21.T11148/076759916209e5d62bd5"

# InfoType PIDs for Grant attributes
INFOTYPES = {
    "funderRorId": "21.T11969/4b9e95b6d60f47c5620f",
    "funderDOI": "21.T11969/8555b1635c61d2339700",
    "funderName": "21.T11969/f3c36b0db75e669a57fa",
    "grantCode": "21.T11969/1c25f48eb6a47b22a9cc",
    "projectName": "21.T11969/112427d2da588bf46e53",
    "projectWebsite": "21.T11969/e9fbabb0285ca091838e",
    "landingPageLocation": "21.T11969/8710d753ad10f371189b",
}


class GrantDesign(RecordDesign):
    """Create Grant FDO records with Grant profile.

    Reusable design for creating Grant FDOs from any metadata source.
    Validates funder IDs (ROR or CrossRef DOI) and creates bidirectional
    funding relations between grants and research outputs.

    The Grant profile documents:
    - Funder identification (via ROR ID or CrossRef Funder DOI)
    - Grant code/number assigned by the funding organization
    - Optional project name and website
    - Links to funded research outputs (datasets, experiments, materials)

    Example:
        ```python
        from fdo_usecases.designs.grant import GrantDesign
        from fdo_usecases.designs.zenodo.models.exchange import GrantFDOData

        graph = {}
        design = GrantDesign(graph)
        data = GrantFDOData(
            funder_ror_id="https://ror.org/018mejw64",
            funder_name="Deutsche Forschungsgemeinschaft",
            grant_code="460247524",
            project_name="NFDI-MatWerk",
            project_website="https://nfdi-matwerk.de"
        )
        grant_id = await design.create_fdo(data)
        # Returns: "grant:https://ror.org/018mejw64::460247524"
        ```

    Attributes:
        _graph: Reference to FDO record graph dictionary
        _created_grants: Set of created grant IDs for deduplication

    """

    def __init__(self, graph: dict[str, PidRecord] | None = None):
        """Initialize the grant design.

        Args:
            graph: Shared FDO record graph dictionary. If None, uses an
                internal empty dict (useful for standalone usage).

        """
        super().__init__()
        self._graph = graph or {}
        self._created_grants: set[str] = set()
        logger.debug("GrantDesign initialized")

    async def create_fdo(self, data) -> str | None:
        """Create Grant FDO with validated funder IDs.

        Creates a PidRecord with the Grant profile and populates it with
        funder information, grant code, and optional project details.

        Validation behavior:
        - **Valid**: Create FDO normally
        - **Recoverable invalid** (e.g., unresolvable DOI): Log warning, create FDO
        - **Blocking invalid** (missing required fields): Log error, skip FDO

        Args:
            data: GrantFDOData object containing grant information including
                at least one funder identifier (ROR ID or CrossRef DOI),
                funder name, and grant code.

        Returns:
            Grant FDO ID string if created successfully (format: `grant:<funder_id>::<grant_code>`),
            None if validation failed with blocking errors.

        """
        grant_id = data.grant_fdo_id

        # Deduplication check
        if grant_id in self._created_grants:
            logger.debug(f"Grant FDO already created: {grant_id}")
            return grant_id

        # Validate funder IDs
        is_valid, message = await self._validate_grant_data(data)

        if not is_valid:
            if "blocking" in message.lower():
                logger.error(f"Skipping Grant FDO {grant_id}: {message}")
                return None
            else:
                logger.warning(
                    f"Creating Grant FDO {grant_id} with warnings: {message}"
                )

        # Create PidRecord
        record = PidRecord()
        record.setId(grant_id)
        record.setPid("")

        # Add Grant profile
        record.addAttribute(PROFILE_KEY, [GRANT_PROFILE_PID])

        # Funder IDs (at least one required)
        if data.funder_ror_id:
            record.addAttribute(INFOTYPES["funderRorId"], data.funder_ror_id)
        if data.funder_crossref_doi:
            record.addAttribute(INFOTYPES["funderDOI"], data.funder_crossref_doi)

        # Required fields
        record.addAttribute(INFOTYPES["funderName"], data.funder_name)
        record.addAttribute(INFOTYPES["grantCode"], data.grant_code)

        # Optional fields
        if data.project_name:
            record.addAttribute(INFOTYPES["projectName"], data.project_name)

        # Landing page (priority: project website → funder ID URL → omit)
        landing_page = None
        if data.project_website:
            landing_page = data.project_website
            record.addAttribute(INFOTYPES["projectWebsite"], data.project_website)
        elif data.funder_ror_id:
            landing_page = data.funder_ror_id
        elif data.funder_crossref_doi:
            landing_page = data.funder_crossref_doi

        if landing_page:
            record.addAttribute(INFOTYPES["landingPageLocation"], landing_page)

        # Store in graph
        if self._graph is not None:
            self._graph[grant_id] = record

        self._created_grants.add(grant_id)

        logger.info(f"Created Grant FDO: {grant_id}")
        return grant_id

    async def _validate_grant_data(self, data) -> tuple[bool, str]:
        """Validate GrantFDOData before FDO creation.

        Performs lightweight validation checking:
        - At least one funder ID is present (ROR or CrossRef DOI)
        - ROR ID format is valid (if provided)

        Note: This does NOT validate against external APIs (ROR/CrossRef).
        For full validation, use FunderIDValidator.

        Args:
            data: GrantFDOData object to validate

        Returns:
            Tuple of (is_valid, message):
            - is_valid: True if validation passed
            - message: Empty string if valid, warning/error message if invalid

        """
        messages = []
        has_blocking_error = False

        # Check at least one funder ID is present
        if not data.funder_ror_id and not data.funder_crossref_doi:
            messages.append("No funder ID provided (requires ROR or CrossRef DOI)")
            has_blocking_error = True

        # Validate ROR ID format if provided
        if data.funder_ror_id:
            ror_clean = data.funder_ror_id.replace("https://ror.org/", "")
            # ROR IDs are typically 9 characters starting with 0
            # Use flexible validation - just check it looks like a ROR ID
            ror_pattern = r"^0[a-z0-9]{6,8}$"
            if not re.match(ror_pattern, ror_clean):
                messages.append(f"Invalid ROR ID format: {data.funder_ror_id}")
                has_blocking_error = True

        # Determine result
        if has_blocking_error:
            error_msg = "; ".join(messages)
            return False, f"blocking: {error_msg}"
        elif messages:
            warning_msg = "; ".join(messages)
            return True, f"warning: {warning_msg}"
        else:
            return True, ""


__all__ = ["GrantDesign", "GRANT_PROFILE_PID"]
