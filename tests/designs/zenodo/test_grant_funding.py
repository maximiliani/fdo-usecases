# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Integration tests for grant funding extraction and FDO creation.

This module tests the complete grant funding workflow:
1. Fetching Zenodo metadata with grant information
2. Extracting ROR IDs from Zenodo internal_id format
3. Creating Grant FDOs with validated funder identifiers
4. Linking datasets to grants via fundedBy relations
5. Overriding with pre-registered grant data when available

Example:
    Run this test directly:
    ```bash
    python -m tests.designs.zenodo.test_grant_funding
    ```

    Or via pytest:
    ```bash
    pytest tests/designs/zenodo/test_grant_funding.py -v
    ```

"""

import asyncio
import json
from pathlib import Path

from fdo_usecases.designer_lib.executor import placeholder_pid
from fdo_usecases.designs.grant import PRE_REGISTERED_GRANTS
from fdo_usecases.designs.zenodo import ZenodoFDODesign


async def test_grant_funding_extraction():
    """Test grant funding extraction and FDO creation from Zenodo metadata.

    This integration test verifies:
    1. Successful fetching of Zenodo metadata with grants
    2. Automatic ROR ID extraction from internal_id format
    3. Grant FDO creation with proper validation
    4. Dataset-to-grant linking via fundedBy relations
    5. Pre-registered grant data override (MatWerk example)

    Raises:
        AssertionError: If any assertion fails
        Exception: If the Zenodo API call fails

    """
    doi = "10.5281/zenodo.20132712"

    print(f"Testing grant funding extraction for {doi}")
    design = ZenodoFDODesign(dois=[doi])
    successful, failed = await design.execute_async()

    assert not failed, f"Zenodo FDO creation failed: {failed}"

    # Find Grant FDOs in graph
    grant_fdos = {
        k: v
        for k, v in design._record_graph.items()
        if k.startswith(placeholder_pid("grant:"))
    }

    print(f"\n✅ Created {len(grant_fdos)} Grant FDO(s):")
    for grant_id, record in grant_fdos.items():
        print(f"\n  {grant_id}")

        # Extract and display attributes
        for attr in record._tuples:
            key, value = attr
            if key in [
                "funderName",
                "grantCode",
                "projectName",
                "projectWebsite",
                "funderRorId",
                "funderCrossRefDoi",
            ]:
                print(f"    {key}: {value}")

    # Verify at least one grant was created
    assert len(grant_fdos) > 0, "No Grant FDOs were created"

    # Find datasets with fundedBy relations
    funded_datasets = [
        (k, v)
        for k, v in design._record_graph.items()
        if any(attr[0] == "21.T11969/funded0000000000001" for attr in v._tuples)
    ]

    print(f"\n📊 Datasets with funding relations: {len(funded_datasets)}")
    assert len(funded_datasets) > 0, "No datasets have fundedBy relations"

    # Verify MatWerk grant exists with correct ID
    matwerk_key = PRE_REGISTERED_GRANTS["matwerk"].unique_key
    expected_grant_id = placeholder_pid(f"grant:{matwerk_key}")

    assert expected_grant_id in grant_fdos, (
        f"MatWerk grant not found: {expected_grant_id}. "
        f"Available grants: {list(grant_fdos.keys())}"
    )
    print(f"\n✅ MatWerk grant found: {expected_grant_id}")

    # Verify MatWerk grant has correct metadata from registry
    matwerk_record = grant_fdos[expected_grant_id]
    # Check that project website from registry was used
    has_website = any(
        attr[0] == "21.T11969/e9fbabb0285ca091838e"
        and attr[1] == "https://nfdi-matwerk.de"
        for attr in matwerk_record._tuples
    )
    assert has_website, "MatWerk grant should have project website from registry"
    print("✅ MatWerk grant has correct project website from registry")

    # Export for manual inspection (optional, useful for debugging)
    output_path = Path(__file__).parent.parent / "grant" / "test_grant_fdo_graph.json"
    graph_dict = {k: v.toSimpleJSON() for k, v in design._record_graph.items()}
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(graph_dict, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Full graph exported to: {output_path}")


def test_grant_funding_sync():
    """Synchronous wrapper for test_grant_funding_extraction.

    This allows running the test via pytest without async configuration.
    """
    asyncio.run(test_grant_funding_extraction())


if __name__ == "__main__":
    # Run when executed directly
    asyncio.run(test_grant_funding_extraction())
    print("\n✅ All tests passed!")
