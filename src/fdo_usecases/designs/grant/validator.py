# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Funder identifier validation utilities.

This module provides the FunderIDValidator class for validating funder
identifiers (ROR IDs and CrossRef Funder DOIs) before creating Grant FDOs.
It includes format validation and optional API-based resolvability checks.

Example:
    ```python
    from fdo_usecases.designs.grant import FunderIDValidator

    async with FunderIDValidator() as validator:
        # Validate ROR ID format
        is_valid = await validator.validate_ror("https://ror.org/018mejw64")

        # Validate CrossRef DOI resolves
        is_resolved = await validator.validate_crossref_doi(
            "10.13039/501100001659"
        )

        # Extract ROR from Zenodo internal_id
        ror_id = await validator.extract_ror_from_zenodo_internal_id(
            "018mejw64::460247524"
        )
        # Returns: "https://ror.org/018mejw64"
    ```

"""

import logging
import re

logger = logging.getLogger(__name__)


class FunderIDValidator:
    """Validate and resolve funder identifiers (ROR/CrossRef).

    This validator provides methods to check the validity of ROR IDs and
    CrossRef Funder DOIs, including format validation and API-based
    resolvability checks.

    The validator uses async context manager pattern to manage API client
    lifecycles efficiently.

    Attributes:
        _crossref_client: CrossRef Funder Registry API client (lazy initialized)
        _ror_client: ROR API client (lazy initialized)

    Example:
        ```python
        async with FunderIDValidator() as validator:
            is_valid, message = await validator.validate_grant_data(grant_data)
            if not is_valid:
                print(f"Validation failed: {message}")
        ```

    """

    #: ROR ID pattern: starts with 0, followed by 6-8 alphanumeric characters
    ROR_PATTERN = re.compile(r"^0[a-z0-9]{6,8}$")

    def __init__(self):
        """Initialize the funder ID validator.

        API clients are lazily initialized on first use within the
        async context manager.

        """
        self._crossref_client = None
        self._ror_client = None

    async def __aenter__(self) -> "FunderIDValidator":
        """Initialize API clients on context manager entry.

        Returns:
            Self instance for use within the context manager

        """
        from fdo_usecases.designs.grant.crossref_funder import CrossrefFunderApiClient
        from fdo_usecases.designs.grant.ror import RorApiClient

        self._crossref_client = CrossrefFunderApiClient(cache_enabled=True)
        self._ror_client = RorApiClient(cache_enabled=True)
        await self._crossref_client.__aenter__()
        await self._ror_client.__aenter__()
        return self

    async def __aexit__(
        self, exc_type: type, exc_val: Exception, exc_tb: object
    ) -> None:
        """Close API clients on context manager exit.

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred

        """
        if self._crossref_client:
            await self._crossref_client.__aexit__(exc_type, exc_val, exc_tb)
        if self._ror_client:
            await self._ror_client.__aexit__(exc_type, exc_val, exc_tb)

    async def validate_ror(self, ror_id: str) -> bool:
        """Check if ROR ID has valid format.

        Performs regex-based format validation without making API calls.
        Checks that the ROR ID matches the expected pattern: starts with 0,
        followed by 6-8 alphanumeric characters.

        Args:
            ror_id: ROR ID URL or bare ID string. Accepts formats like:
                - "https://ror.org/018mejw64"
                - "018mejw64"

        Returns:
            True if the ROR ID format is valid, False otherwise.

        Example:
            >>> await validator.validate_ror("https://ror.org/018mejw64")
            True
            >>> await validator.validate_ror("invalid-id")
            False

        """
        # Extract bare ROR ID from URL
        ror_clean = ror_id.replace("https://ror.org/", "")
        is_valid = bool(self.ROR_PATTERN.match(ror_clean))

        if not is_valid:
            logger.debug(f"Invalid ROR ID format: {ror_id}")
        else:
            logger.debug(f"Valid ROR ID format: {ror_id}")

        return is_valid

    async def validate_crossref_doi(self, doi: str) -> bool:
        """Check if CrossRef funder DOI resolves via API.

        Makes an API call to the CrossRef Funder Registry to verify that
        the DOI resolves to a valid funder record.

        Args:
            doi: Funder DOI in any format. Accepts:
                - "10.13039/501100001659"
                - "https://doi.org/10.13039/501100001659"

        Returns:
            True if the DOI resolves to a funder record, False otherwise.
            Returns True if API client is unavailable (graceful degradation).

        Example:
            >>> await validator.validate_crossref_doi("10.13039/501100001659")
            True  # DFG funder DOI resolves

        """
        if self._crossref_client is None:
            logger.warning("CrossRef client not initialized - skipping validation")
            return True  # Assume valid if client not available

        funder_data = await self._crossref_client.get_funder(doi)
        is_valid = funder_data is not None and bool(funder_data)

        if not is_valid:
            logger.debug(f"CrossRef DOI does not resolve: {doi}")
        else:
            logger.debug(f"CrossRef DOI resolves successfully: {doi}")

        return is_valid

    async def extract_ror_from_zenodo_internal_id(self, internal_id: str) -> str | None:
        """Extract ROR ID from Zenodo internal_id format.

        Zenodo uses an internal grant identifier format that combines
        the ROR ID prefix with the grant code: `<ror_id>::<grant_code>`.
        This method extracts and validates the ROR ID portion.

        Args:
            internal_id: Zenodo internal grant identifier string, e.g.,
                "018mejw64::460247524"

        Returns:
            ROR ID URL if extractable and valid (e.g., "https://ror.org/018mejw64"),
            None if extraction fails or format is invalid.

        Example:
            >>> await validator.extract_ror_from_zenodo_internal_id(
            ...     "018mejw64::460247524"
            ... )
            'https://ror.org/018mejw64'

        """
        if "::" not in internal_id:
            logger.debug(f"No '::' separator in internal_id: {internal_id}")
            return None

        ror_part = internal_id.split("::")[0]

        if self.ROR_PATTERN.match(ror_part):
            ror_url = f"https://ror.org/{ror_part}"
            logger.debug(f"Extracted ROR ID from internal_id: {ror_url}")
            return ror_url

        logger.debug(f"Invalid ROR format in internal_id: {internal_id}")
        return None

    async def validate_grant_data(self, data) -> tuple[bool, str]:
        """Validate grant data before FDO creation.

        Comprehensive validation of grant data including:
        - Presence of at least one funder ID (ROR or CrossRef DOI)
        - ROR ID format validation (if provided)
        - CrossRef DOI resolvability check (if provided and API available)

        Validation severity levels:
        - **Blocking errors**: Missing funder IDs, invalid ROR format
        - **Warnings**: Unresolvable CrossRef DOI (but has valid ROR)

        Args:
            data: Object with the following attributes:
                - funder_ror_id: ROR identifier URL (optional)
                - funder_crossref_doi: CrossRef Funder DOI (optional)
                - grant_code: Grant award code

        Returns:
            Tuple of (is_valid, message):
            - is_valid: True if validation passed (may have warnings)
            - message: Empty string if valid, warning/error message if issues found
                - "blocking: <error>" for blocking errors
                - "warning: <warning>" for non-blocking warnings

        Example:
            >>> is_valid, message = await validator.validate_grant_data(grant_data)
            >>> if not is_valid:
            ...     if "blocking" in message:
            ...         print(f"Cannot create FDO: {message}")
            ...     else:
            ...         print(f"Proceeding with warnings: {message}")

        """
        messages = []
        has_blocking_error = False

        # Validate ROR ID if provided
        if data.funder_ror_id:
            is_valid_format = await self.validate_ror(data.funder_ror_id)
            if not is_valid_format:
                messages.append(f"Invalid ROR ID format: {data.funder_ror_id}")
                has_blocking_error = True
            else:
                logger.debug(f"ROR ID format valid: {data.funder_ror_id}")

        # Validate CrossRef DOI if provided
        if data.funder_crossref_doi:
            is_resolved = await self.validate_crossref_doi(data.funder_crossref_doi)
            if not is_resolved:
                # Non-resolving DOI is a warning, not blocking
                messages.append(
                    f"CrossRef DOI does not resolve: {data.funder_crossref_doi}"
                )
            else:
                logger.debug(f"CrossRef DOI resolved: {data.funder_crossref_doi}")

        # Check at least one funder ID is present
        if not data.funder_ror_id and not data.funder_crossref_doi:
            messages.append("No funder ID provided (requires ROR or CrossRef DOI)")
            has_blocking_error = True

        # Determine result
        if has_blocking_error:
            error_msg = "; ".join(messages)
            logger.error(f"Grant validation failed (blocking): {error_msg}")
            return False, f"blocking: {error_msg}"
        elif messages:
            warning_msg = "; ".join(messages)
            logger.warning(f"Grant validation warnings: {warning_msg}")
            return True, f"warning: {warning_msg}"
        else:
            logger.debug(f"Grant validation passed for {data.grant_code}")
            return True, ""


__all__ = ["FunderIDValidator"]
