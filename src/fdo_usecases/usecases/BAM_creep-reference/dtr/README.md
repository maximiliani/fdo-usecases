# FDO Type Registry Documents for BAM Creep-Reference Use Cases

This directory contains JSON documents for registering FDO types in the Type Registry (https://typeregistry.lab.pidconsortium.net) for BAM creep-reference use cases.

## Standards & References

### Primary Standards
- **DIN EN ISO 204:2023-10**: Metallic materials — Uniaxial creep testing in tension — Method of test
  - DOI: https://dx.doi.org/10.31030/3485273
  - URL: https://www.dinmedia.de/en/standard/din-en-iso-204/371676068

### Identifier Systems
- **ORCID**: https://orcid.org — Persistent identifiers for researchers
- **ROR**: https://ror.org — Research organization identifiers
- **DOI**: https://www.doi.org/ — Digital Object Identifiers
- **Handle**: https://www.handle.net/ — Persistent identifier system

### Licensing & Classification
- **SPDX**:
  - Specification v3.0.1: https://spdx.github.io/spdx-spec/v3.0.1/
  - License List: https://spdx.org/licenses/
- **DataCite Metadata Schema**:
  - ResourceTypeGeneral: https://datacite-metadata-schema.readthedocs.io/en/4.7/properties/resourcetype/#a-resourcetypegeneral

### Technical Standards
- **ISO 8601**: Date and time format — https://www.iso.org/iso-8601-date-and-time-format.html
- **Semantic Versioning**: https://semver.org
- **MIME Media Types**: https://www.iana.org/assignments/media-types/media-types.xhtml

### Institutional Frameworks
- **Helmholtz Association**: https://www.helmholtz.de/en/research/
- **NFDI (National Research Data Infrastructure)**: https://www.nfdi.de/

## Directory Structure

```
dtr/
├── measurement_units/    # 1 MeasurementUnit definition (MegaPascal)
├── basic_info_types/     # 6 new BasicInfoType definitions
├── info_types/           # 37 InfoType (attribute) definitions
└── profiles/             # 8 Profile definitions
```

## Registration Order

**CRITICAL**: Types must be registered in the following order due to PID dependencies:

### Phase 1: MeasurementUnits
Register first to obtain PIDs for linking from BasicInfoTypes.

| File | Placeholder PID | Description |
|------|----------------|-------------|
| `measurement_units/MegaPascal.json` | `<<PLACEHOLDER>>` | MPa unit for stress/pressure |

### Phase 2: BasicInfoTypes
Register to obtain PIDs for use in InfoTypes.

| File | Placeholder PID | Description | Replaces/Extends |
|------|----------------|-------------|------------------|
| `basic_info_types/ORCID_URL.json` | `<<PLACEHOLDER>>` | ORCID URL format | New |
| `basic_info_types/SPDX_URL.json` | `<<PLACEHOLDER>>` | SPDX license URL format | New |
| `basic_info_types/SemVerVersion.json` | `<<PLACEHOLDER>>` | Semantic version (vMajor.Minor.Fix) | New |
| `basic_info_types/DecimalNumber.json` | `<<PLACEHOLDER>>` | Decimal number for measurements | New |
| `basic_info_types/Percentage.json` | `<<PLACEHOLDER>>` | Ratio [0-1] | New |
| `basic_info_types/DecimalAngle.json` | `<<PLACEHOLDER>>` | Angle in degrees [0-360] | New |

**Existing BasicInfoTypes reused (no registration needed):**
- String: `21.T11969/3df63b7acb0522da685d`
- URL: `21.T11969/e0efc41346cda4ba84ca`
- DateTime: `21.T11969/f1e5baf5ecc358963108`
- Duration: `21.T11969/1370004da76fa4f3b7a5`
- ror: `21.T11969/9810c562f8a6deb1f22c`
- doi_identifier: `21.T11969/48ba02e08f1185e3f854`
- handle_identifier: `21.T11969/3bbedeeb04fa80daf501`

### Phase 3: InfoTypes
After obtaining BasicInfoType PIDs, update all `<<PLACEHOLDER_*>>` values in InfoTypes and register.

**InfoTypes requiring placeholder updates:**
| File | Requires PID from |
|------|------------------|
| `creator.json` | ORCID_URL |
| `spdxLicense.json` | SPDX_URL |
| `version.json` | SemVerVersion |
| `specifiedTemperature.json` | DecimalNumber |
| `initialStress.json` | DecimalNumber |
| `percentageCreepExtension.json` | Percentage |
| `SingleCrystalOrientation.json` | DecimalAngle |

All other InfoTypes reference existing BasicInfoType PIDs.

### Phase 4: Profiles
After obtaining InfoType PIDs, update all `<<PLACEHOLDER_*>>` values in profiles and register.

| Profile | InfoTypes Used |
|---------|---------------|
| `Base.json` | kernelInformationProfile, creatorAffiliation, creator, dateCreated, dateModified, keyword, name, description |
| `Helmholtz.json` | helmholtzResearchArea, helmholtzPoFStructure |
| `NFDI.json` | nfdiConsortia, grantNumber |
| `Versionable.json` | version, nextVersion, previousVersion, latestVersion |
| `DataResource.json` | mimeType, dataObjectLocation, spdxLicense, checksum |
| `Publication.json` | doi, dataCitePublicationType, publisher, datePublished, creator |
| `CreepExperiment.json` | applicableStandard, testID, specifiedTemperature, initialStress, testDuration, percentageCreepExtension, SingleCrystalOrientation, hasData, hasMetadata, usesMaterial |
| `Material.json` | materialID, previewImage, semImage, hasChemicalComposition, hasHeatTreatment |

## Schema Compliance Notes

### BasicInfoType Structure
Each BasicInfoType includes:
- **Schema**: Defines datatype (String/Number/Boolean/Enum) with constraints (pattern, minimum, maximum)
- **ExpectedUse**: Generalized usage description beyond this specific use case
- **References**: External standards and specifications
- **Aliases**: Alternative names for discoverability
- **versioning**: Version tracking with previousVersion/nextVersion support

### InfoType Structure
Each InfoType is an **Object** type with a single property:
- Property **Name** matches the InfoType name
- Property **Type** references a BasicInfoType PID
- Property **Properties.Cardinality** is always `"1"` (profile controls repetition)
- Property **Properties.extractProperties** is `true` (flattens structure)

### Profile Structure
Each profile property includes:
- **Name**: Matches the InfoType name
- **Title**: Human-readable label
- **Description**: Inherited from InfoType
- **Type**: InfoType PID
- **Properties.Cardinality**: One of `"1"`, `"0 - 1"`, `"1 - n"`, `"0 - n"`

## Units of Measurement

### Registered MeasurementUnit
- **MegaPascal** (`<<PLACEHOLDER>>`): MPa = 10⁶ Pa, derived from SI-Pascal

### Existing MeasurementUnits Reused
- **SI-Celsius**: `21.T11969/d878eec28d528a3ee5e8` — Temperature in °C
- **SI-Pascal**: `21.T11969/9be4ec7c88f130ac2598` — Base for MPa derivation
- **SI-Second**: `21.T11969/98a41ea06b3ab0df372a` — Time duration base

### Unit Usage per DIN EN ISO 204:2023-10
| Quantity | Unit | Symbol | BasicInfoType |
|----------|------|--------|---------------|
| Temperature | degree Celsius | °C | DecimalNumber |
| Stress | megapascal | MPa | DecimalNumber |
| Duration | hour/second | h/s | ISO8601-Duration |
| Creep strain | ratio (dimensionless) | — | Percentage |
| Orientation | degree | ° | DecimalAngle |

## Contributor

Maximilian Inckmann
ORCID: https://orcid.org/0009-0005-2800-4833
Karlsruhe Institute for Technology

## FAIR Digital Object Principles

These types support FAIR principles:
- **Findable**: Rich metadata with persistent identifiers (DOI, Handle, ORCID, ROR)
- **Accessible**: Standardized access protocols via URLs and resolver services
- **Interoperable**: Common vocabularies (SPDX, DataCite, ISO standards)
- **Reusable**: Clear licensing, provenance, and domain-specific semantics
