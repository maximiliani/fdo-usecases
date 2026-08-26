# Grant FDO Design Module

This module provides a comprehensive toolkit for creating **Grant FDOs** (Findable Digital Objects) that document research funding information. It supports multiple funder identifier systems (ROR IDs and CrossRef Funder DOIs), validation utilities, and a static registry for authoritative grant data.

## Overview

The Grant module enables you to:

- Create Grant FDO records compliant with the Grant profile
- Validate funder identifiers (format and resolvability)
- Manage pre-registered grants with authoritative information
- Extract funder IDs from Zenodo metadata automatically
- Establish bidirectional funding relationships between grants and research outputs

## Architecture

```
fdo_usecases/designs/grant/
├── __init__.py           # Public API exports
├── README.md             # This file
├── grant_design.py       # GrantDesign class for FDO creation
├── registry.py           # Static grant registry
├── validator.py          # Funder ID validation utilities
├── crossref_funder.py    # CrossRef Funder Registry API client
└── ror.py                # ROR API client
```

## Quick Start

### Creating a Grant FDO

```python
from fdo_usecases.designs.grant import GrantDesign
from fdo_usecases.designs.zenodo.models.exchange import GrantFDOData

# Initialize design with shared graph
graph = {}
design = GrantDesign(graph)

# Prepare grant data
data = GrantFDOData(
    funder_ror_id="https://ror.org/018mejw64",
    funder_name="Deutsche Forschungsgemeinschaft",
    grant_code="460247524",
    project_name="NFDI-MatWerk",
    project_website="https://nfdi-matwerk.de"
)

# Create the Grant FDO
grant_id = await design.create_fdo(data)
print(f"Created: {grant_id}")
# Output: "grant:https://ror.org/018mejw64::460247524"
```

### Validating Funder Identifiers

```python
from fdo_usecases.designs.grant import FunderIDValidator

async with FunderIDValidator() as validator:
    # Format validation (no API call)
    is_valid = await validator.validate_ror("https://ror.org/018mejw64")

    # Resolvability check (API call)
    is_resolved = await validator.validate_crossref_doi(
        "10.13039/501100001659"
    )

    # Extract ROR from Zenodo internal_id
    ror_id = await validator.extract_ror_from_zenodo_internal_id(
        "018mejw64::460247524"
    )
    # Returns: "https://ror.org/018mejw64"
```

### Using Pre-Registered Grants

```python
from fdo_usecases.designs.grant import PRE_REGISTERED_GRANTS

# Access MatWerk grant
matwerk = PRE_REGISTERED_GRANTS["matwerk"]
print(matwerk.funder_name)  # "Deutsche Forschungsgemeinschaft"
print(matwerk.project_website)  # "https://nfdi-matwerk.de"
print(matwerk.unique_key)  # "https://ror.org/018mejw64::460247524"

# Check if a grant is pre-registered
key = "https://ror.org/018mejw64::460247524"
if key in [entry.unique_key for entry in PRE_REGISTERED_GRANTS.values()]:
    print("Grant is pre-registered with authoritative data")
```

## Components

### GrantDesign

The main class for creating Grant FDO records. It:

- Validates funder identifiers (ROR format, optional CrossRef resolution)
- Creates PidRecords with the Grant profile
- Handles deduplication (same grant = one FDO)
- Manages landing page URLs (priority: project website → funder ID → omit)

**Validation Behavior:**
- ✅ **Valid**: Creates FDO normally
- ⚠️ **Recoverable invalid** (e.g., unresolvable DOI but valid ROR): Logs warning, creates FDO
- ❌ **Blocking invalid** (missing funder IDs, invalid ROR format): Logs error, skips FDO

### GrantRegistryEntry & PRE_REGISTERED_GRANTS

Static registry for authoritative grant information. Pre-registered grants take precedence over automatically extracted data from sources like Zenodo.

**Use cases:**
- Ensuring consistent funder names across datasets
- Providing project websites not available in source metadata
- Correcting errors in automatically extracted data

**Adding new entries:**
```python
PRE_REGISTERED_GRANTS["my_grant"] = GrantRegistryEntry(
    funder_name="Example Foundation",
    grant_code="EX-12345",
    funder_ror_id="https://ror.org/xxxxxxxxx",
    project_name="Example Project",
    project_website="https://example.org"
)
```

### CrossrefFunderApiClient

Async HTTP client for the [CrossRef Funder Registry](https://www.crossref.org/services/funder-registry/). Provides:

- Funder lookup by DOI
- Name-based search
- Response caching for performance

### RorApiClient

Async HTTP client for the [ROR API](https://ror.org/). Provides:

- Organization lookup by ROR ID
- Name-based search
- Response caching for performance

### FunderIDValidator

Comprehensive validation utility combining format checks and API-based resolvability. Use within an async context manager for efficient API client management.

## Grant Profile Schema

The Grant profile documents:

| Property | Type | Cardinality | Description |
|----------|------|-------------|-------------|
| `funderRorId` | ROR URL | 0-1 | ROR identifier for funding organization |
| `funderDOI` | DOI URL | 0-1 | Funder DOI (e.g., from CrossRef Funder Registry) |
| `funderName` | String | 1 | Human-readable funder name (required) |
| `grantCode` | String | 1 | Grant award number/code (required) |
| `projectName` | String | 0-1 | Official project title |
| `projectWebsite` | URL | 0-1 | Project website URL |
| `funds` | Handle | 0-n | Links to funded research outputs |

**Constraint:** At least one of `funderRorId` OR `funderDOI` must be present.

## Integration with Zenodo

The Zenodo orchestrator automatically:

1. Extracts grant information from Zenodo API responses
2. Converts ROR IDs from Zenodo's `internal_id` format (`018mejw64::460247524`)
3. Deduplicates grants by unique key (`<funder_id>::<grant_code>`)
4. Overrides with pre-registered grant data when available
5. Creates Grant FDOs and links datasets via `fundedBy` relations

```python
from fdo_usecases.designs.zenodo import ZenodoFDODesign

design = ZenodoFDODesign(dois=["10.5281/zenodo.20132712"])
await design.execute_async()

# Grant FDOs are automatically created and linked
grant_fdos = {k: v for k, v in design._record_graph.items()
              if k.startswith("grant:")}
```

## Testing

Run the test suite:

```bash
# Run grant funding integration test
python -m fdo_usecases.usecases.bam_creep_reference.test_grant_funding

# Run unit tests (when available)
pytest tests/designs/test_grant.py
```

## License

SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
SPDX-License-Identifier: Apache-2.0
