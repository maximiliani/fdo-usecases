# FDO Type Registry Types for BAM Creep-Reference Use Cases

This document lists all BasicInfoTypes, InfoTypes, and Profiles with their Type Registry PIDs, local JSON file
references, and DTR entry links.

**Last Updated**: 2026-07-01
**Contributor**: Maximilian Inckmann, ORCID: https://orcid.org/0009-0005-2800-4833
**Standard Reference**: DIN EN ISO 204:
2023-10 — [DOI](https://dx.doi.org/10.31030/3485273) | [DIN Media](https://www.dinmedia.de/en/standard/din-en-iso-204/371676068)

---

## Table of Contents

- [MeasurementUnits](#measurementunits)
- [BasicInfoTypes (Syntax Definitions)](#basicinfotypes-syntax-definitions)
  - [Newly Created](#newly-created)
  - [Existing (Reused from Type Registry)](#existing-reused-from-type-registry)
- [InfoTypes (Attributes)](#infotypes-attributes)
- [Profiles](#profiles)
  - [Base](#base)
  - [Helmholtz](#helmholtz)
  - [NFDI](#nfdi)
  - [Versionable](#versionable)
  - [DataResource](#dataresource)
  - [Publication](#publication)
  - [CreepExperiment](#creepexperiment)
  - [Material](#material)
- [Registration Status Summary](#registration-status-summary)
- [External References](#external-references)
  - [Standards](#standards)
  - [Identifier Systems](#identifier-systems)
  - [Licensing & Classification](#licensing--classification)
  - [Technical Standards](#technical-standards)
  - [Institutional Frameworks](#institutional-frameworks)

---

## MeasurementUnits

| Name       | PID                              | Local File                                                                   | DTR Entry                                                                                 |
|------------|----------------------------------|------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------|
| MegaPascal | `21.T11969/6291bafa30dfead575e8` | [`dtr/measurement_units/MegaPascal.json`](measurement_units/MegaPascal.json) | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/6291bafa30dfead575e8) |

---

## BasicInfoTypes (Syntax Definitions)

### Newly Created

| Name                      | PID                              | Local File                                                                          | DTR Entry                                                                                 | Description                           |
|---------------------------|----------------------------------|-------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------|---------------------------------------|
| ORCID_URL                 | `21.T11969/fee5f6c1a7da0c627591` | [`ORCID_URL.json`](basic_info_types/ORCID_URL.json)                                 | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/fee5f6c1a7da0c627591) | URL format of ORCID identifier        |
| SPDX_URL                  | `21.T11969/c153e86078bc231756ac` | [`SPDX_URL.json`](basic_info_types/SPDX_URL.json)                                   | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/c153e86078bc231756ac) | URL format of SPDX license identifier |
| SemVerVersion             | `21.T11969/965752be13522e6032a4` | [`SemVerVersion.json`](basic_info_types/SemVerVersion.json)                         | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/965752be13522e6032a4) | Semantic version (vMajor.Minor.Fix)   |
| DecimalNumber             | `21.T11969/112c248def0a38f01234` | [`DecimalNumber.json`](basic_info_types/DecimalNumber.json)                         | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/112c248def0a38f01234) | Decimal number for measurements       |
| Percentage                | `21.T11969/c4519ac7ccbe73f10f9d` | [`Percentage.json`](basic_info_types/Percentage.json)                               | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/c4519ac7ccbe73f10f9d) | Ratio [0–1]                           |
| DecimalAngle              | `21.T11969/2fe7b9f68268094eb3d2` | [`DecimalAngle.json`](basic_info_types/DecimalAngle.json)                           | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/2fe7b9f68268094eb3d2) | Angle in degrees [0–360]              |
| HelmholtzResearchAreaEnum | `21.T11969/2170780414163d16542d` | [`HelmholtzResearchAreaEnum.json`](basic_info_types/HelmholtzResearchAreaEnum.json) | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/2170780414163d16542d) | Enum of 6 Helmholtz research areas    |

### Existing (Reused from Type Registry)

| Name              | PID                              | DTR Entry                                                                                 | Description                 |
|-------------------|----------------------------------|-------------------------------------------------------------------------------------------|-----------------------------|
| String            | `21.T11969/3df63b7acb0522da685d` | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/3df63b7acb0522da685d) | Text string                 |
| URL               | `21.T11969/e0efc41346cda4ba84ca` | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/e0efc41346cda4ba84ca) | URL format                  |
| DateTime          | `21.T11969/f1e5baf5ecc358963108` | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/f1e5baf5ecc358963108) | ISO 8601 datetime           |
| Duration          | `21.T11969/1370004da76fa4f3b7a5` | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/1370004da76fa4f3b7a5) | ISO 8601 duration           |
| ror               | `21.T11969/9810c562f8a6deb1f22c` | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/9810c562f8a6deb1f22c) | ROR organization identifier |
| doi_identifier    | `21.T11969/48ba02e08f1185e3f854` | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/48ba02e08f1185e3f854) | DOI identifier schema       |
| handle_identifier | `21.T11969/3bbedeeb04fa80daf501` | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/3bbedeeb04fa80daf501) | Handle identifier schema    |

---

## InfoTypes (Attributes)

All InfoTypes are Object types with a single property that extracts the underlying value (`extractProperties: true`).
Cardinality is defined at the Profile level.

| Name                     | PID                              | Local File                                                                  | DTR Entry                                                                                 | Base Type                 |
|--------------------------|----------------------------------|-----------------------------------------------------------------------------|-------------------------------------------------------------------------------------------|---------------------------|
| SingleCrystalOrientation | `21.T11969/4597cf0db467d7e365a9` | [`SingleCrystalOrientation.json`](info_types/SingleCrystalOrientation.json) | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/4597cf0db467d7e365a9) | DecimalAngle              |
| applicableStandard       | `21.T11969/dda596702b20205cba36` | [`applicableStandard.json`](info_types/applicableStandard.json)             | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/dda596702b20205cba36) | String                    |
| checksum                 | `21.T11969/a80ed2ef79e22f1d8af8` | [`checksum.json`](info_types/checksum.json)                                 | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/a80ed2ef79e22f1d8af8) | String                    |
| cites                    | `21.T11969/813e06c1441327b72e68` | [`cites.json`](info_types/cites.json)                                       | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/813e06c1441327b72e68) | handle_identifier         |
| creator                  | `21.T11969/7c67083a5d218e544063` | [`creator.json`](info_types/creator.json)                                   | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/7c67083a5d218e544063) | ORCID_URL                 |
| creatorAffiliation       | `21.T11969/ea9f6b3d78c6608fe801` | [`creatorAffiliation.json`](info_types/creatorAffiliation.json)             | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/ea9f6b3d78c6608fe801) | ror                       |
| dataCitePublicationType  | `21.T11969/48dbf6a89f9748ae4ead` | [`dataCitePublicationType.json`](info_types/dataCitePublicationType.json)   | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/48dbf6a89f9748ae4ead) | String                    |
| dataObjectLocation       | `21.T11969/479febb2bbe8400da547` | [`dataObjectLocation.json`](info_types/dataObjectLocation.json)             | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/479febb2bbe8400da547) | URL                       |
| dateCreated              | `21.T11969/29f92bd203dd3eaa5a1f` | [`dateCreated.json`](info_types/dateCreated.json)                           | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/29f92bd203dd3eaa5a1f) | DateTime                  |
| dateModified             | `21.T11969/397d831aa3a9d18eb52c` | [`dateModified.json`](info_types/dateModified.json)                         | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/397d831aa3a9d18eb52c) | DateTime                  |
| datePublished            | `21.T11969/0c9b86e828976a85d4f2` | [`datePublished.json`](info_types/datePublished.json)                       | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/0c9b86e828976a85d4f2) | DateTime                  |
| description              | `21.T11969/880724416f5857987e70` | [`description.json`](info_types/description.json)                           | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/880724416f5857987e70) | String                    |
| doi                      | `21.T11969/48e563f148dc04d8b31c` | [`doi.json`](info_types/doi.json)                                           | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/48e563f148dc04d8b31c) | doi_identifier            |
| grantNumber              | `21.T11969/1c25f48eb6a47b22a9cc` | [`grantNumber.json`](info_types/grantNumber.json)                           | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/1c25f48eb6a47b22a9cc) | String                    |
| hasChemicalComposition   | `21.T11969/e32cfb93d7fc61ce3ca5` | [`hasChemicalComposition.json`](info_types/hasChemicalComposition.json)     | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/e32cfb93d7fc61ce3ca5) | handle_identifier         |
| hasData                  | `21.T11969/cc230f978e8add2e2520` | [`hasData.json`](info_types/hasData.json)                                   | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/cc230f978e8add2e2520) | handle_identifier         |
| hasHeatTreatment         | `21.T11969/766ae14d72b49cfb5273` | [`hasHeatTreatment.json`](info_types/hasHeatTreatment.json)                 | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/766ae14d72b49cfb5273) | handle_identifier         |
| hasPart                  | `21.T11969/39c056d0cc63e2d0ff17` | [`hasPart.json`](info_types/hasPart.json)                                   | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/39c056d0cc63e2d0ff17) | handle_identifier         |
| hasMetadata              | `21.T11969/d0773859091aeb451528` | [`hasMetadata.json`](info_types/hasMetadata.json)                           | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/d0773859091aeb451528) | handle_identifier         |
| helmholtzPoFStructure    | `21.T11969/e5cb2389246c17ee0503` | [`helmholtzPoFStructure.json`](info_types/helmholtzPoFStructure.json)       | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/e5cb2389246c17ee0503) | String                    |
| helmholtzResearchArea    | `21.T11969/ed4732b6dc70be0f1b22` | [`helmholtzResearchArea.json`](info_types/helmholtzResearchArea.json)       | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/ed4732b6dc70be0f1b22) | HelmholtzResearchAreaEnum |
| isPartOf                 | `21.T11969/30f4a1f8aacab81faf38` | [`isPartOf.json`](info_types/isPartOf.json)                                 | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/30f4a1f8aacab81faf38) | handle_identifier         |
| initialStress            | `21.T11969/8bd53487030550ee2e94` | [`initialStress.json`](info_types/initialStress.json)                       | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/8bd53487030550ee2e94) | DecimalNumber             |
| isCitedBy                | `21.T11969/520bb71b795d8573f533` | [`isCitedBy.json`](info_types/isCitedBy.json)                               | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/520bb71b795d8573f533) | handle_identifier         |
| isReferencedBy           | `21.T11969/e5945ef3ff07f314a146` | [`isReferencedBy.json`](info_types/isReferencedBy.json)                     | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/e5945ef3ff07f314a146) | handle_identifier         |
| keyword                  | `21.T11969/793ff5c33c3aeb32907a` | [`keyword.json`](info_types/keyword.json)                                   | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/793ff5c33c3aeb32907a) | String                    |
| latestVersion            | `21.T11969/2b4d6ceda80ddd63f7a9` | [`latestVersion.json`](info_types/latestVersion.json)                       | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/2b4d6ceda80ddd63f7a9) | handle_identifier         |
| materialID               | `21.T11969/716805eef0349802dc9a` | [`materialID.json`](info_types/materialID.json)                             | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/716805eef0349802dc9a) | String                    |
| mimeType                 | `21.T11969/3313b863118ed5eb0ded` | [`mimeType.json`](info_types/mimeType.json)                                 | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/3313b863118ed5eb0ded) | String                    |
| name                     | `21.T11969/bd3e9fb9b606d2198c9e` | [`name.json`](info_types/name.json)                                         | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/bd3e9fb9b606d2198c9e) | String                    |
| nextVersion              | `21.T11969/7f1a6afddcfeefbf195b` | [`nextVersion.json`](info_types/nextVersion.json)                           | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/7f1a6afddcfeefbf195b) | handle_identifier         |
| nfdiConsortia            | `21.T11969/3b01aa9a09f0fab04265` | [`nfdiConsortia.json`](info_types/nfdiConsortia.json)                       | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/3b01aa9a09f0fab04265) | String                    |
| percentageCreepExtension | `21.T11969/4be978cac878da94105e` | [`percentageCreepExtension.json`](info_types/percentageCreepExtension.json) | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/4be978cac878da94105e) | Percentage                |
| previewImage             | `21.T11969/925e3f9925a88476ffba` | [`previewImage.json`](info_types/previewImage.json)                         | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/925e3f9925a88476ffba) | URL                       |
| previousVersion          | `21.T11969/7c97f00a2a95826c1a8f` | [`previousVersion.json`](info_types/previousVersion.json)                   | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/7c97f00a2a95826c1a8f) | handle_identifier         |
| publisher                | `21.T11969/cdd96207a7dfbcc0db93` | [`publisher.json`](info_types/publisher.json)                               | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/cdd96207a7dfbcc0db93) | String                    |
| references               | `21.T11969/f4c9a69f715c3c60aa2f` | [`references.json`](info_types/references.json)                             | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/f4c9a69f715c3c60aa2f) | handle_identifier         |
| semImage                 | `21.T11969/19a94f596420bb274408` | [`semImage.json`](info_types/semImage.json)                                 | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/19a94f596420bb274408) | handle_identifier         |
| spdxLicense              | `21.T11969/623654b1072ae7b88202` | [`spdxLicense.json`](info_types/spdxLicense.json)                           | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/623654b1072ae7b88202) | SPDX_URL                  |
| specifiedTemperature     | `21.T11969/ac4a911ffb09772718e3` | [`specifiedTemperature.json`](info_types/specifiedTemperature.json)         | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/ac4a911ffb09772718e3) | DecimalNumber             |
| testDuration             | `21.T11969/7e84faadd49ac88d02b8` | [`testDuration.json`](info_types/testDuration.json)                         | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/7e84faadd49ac88d02b8) | Duration                  |
| testID                   | `21.T11969/1a34a6966f91cc341f58` | [`testID.json`](info_types/testID.json)                                     | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/1a34a6966f91cc341f58) | String                    |
| usesMaterial             | `21.T11969/2dced98076fda9cbf0ef` | [`usesMaterial.json`](info_types/usesMaterial.json)                         | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/2dced98076fda9cbf0ef) | handle_identifier         |
| version                  | `21.T11969/be1ae3492b235faad933` | [`version.json`](info_types/version.json)                                   | [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/be1ae3492b235faad933) | SemVerVersion             |

---

## Profiles

Profiles combine InfoTypes with specific cardinalities. Property names match InfoType names.

### Base

**PID**: `21.T11969/077fe9c54ed5ed26fa54`
**Local File**: [`Base.json`](profiles/Base.json)
**DTR Entry**: [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/077fe9c54ed5ed26fa54)

| Property                 | InfoType                 | Cardinality |
|--------------------------|--------------------------|-------------|
| kernelInformationProfile | kernelInformationProfile | 1..n        |
| creatorAffiliation       | creatorAffiliation       | 1..n        |
| creator                  | creator                  | 1..n        |
| dateCreated              | dateCreated              | 1           |
| dateModified             | dateModified             | 0..1        |
| keyword                  | keyword                  | 1..n        |
| name                     | name                     | 1           |
| description              | description              | 1           |

### Helmholtz

**PID**: `21.T11969/4f19ada2a020aaa8a14a`
**Local File**: [`Helmholtz.json`](profiles/Helmholtz.json)
**DTR Entry**: [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/4f19ada2a020aaa8a14a)

| Property              | InfoType              | Cardinality |
|-----------------------|-----------------------|-------------|
| helmholtzResearchArea | helmholtzResearchArea | 1..n        |
| helmholtzPoFStructure | helmholtzPoFStructure | 1..n        |

### NFDI

**PID**: `21.T11969/175a75397933f1b370af`
**Local File**: [`NFDI.json`](profiles/NFDI.json)
**DTR Entry**: [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/175a75397933f1b370af)

| Property      | InfoType      | Cardinality |
|---------------|---------------|-------------|
| nfdiConsortia | nfdiConsortia | 1..n        |
| grantNumber   | grantNumber   | 1..n        |

### Versionable

**PID**: `21.T11969/6c663a0695a411803d70`
**Local File**: [`Versionable.json`](profiles/Versionable.json)
**DTR Entry**: [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/6c663a0695a411803d70)

| Property        | InfoType        | Cardinality |
|-----------------|-----------------|-------------|
| version         | version         | 1           |
| nextVersion     | nextVersion     | 0..1        |
| previousVersion | previousVersion | 0..1        |
| latestVersion   | latestVersion   | 0..1        |

### DataResource

**PID**: `21.T11969/0738c2ef35faef0fb552`
**Local File**: [`DataResource.json`](profiles/DataResource.json)
**DTR Entry**: [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/0738c2ef35faef0fb552)

| Property           | InfoType           | Cardinality |
|--------------------|--------------------|-------------|
| mimeType           | mimeType           | 1           |
| dataObjectLocation | dataObjectLocation | 1..n        |
| spdxLicense        | spdxLicense        | 1..n        |
| checksum           | checksum           | 1           |

### Publication

**PID**: `21.T11969/e00441c49bf6cb62a4a5`
**Local File**: [`Publication.json`](profiles/Publication.json)
**DTR Entry**: [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/e00441c49bf6cb62a4a5)

| Property                | InfoType                | Cardinality |
|-------------------------|-------------------------|-------------|
| doi                     | doi                     | 1           |
| dataCitePublicationType | dataCitePublicationType | 1           |
| publisher               | publisher               | 1           |
| datePublished           | datePublished           | 0..1        |
| creator                 | creator                 | 1..n        |

### CreepExperiment

**PID**: `21.T11969/222fb86c0b3bece35729`
**Local File**: [`CreepExperiment.json`](profiles/CreepExperiment.json)
**DTR Entry**: [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/222fb86c0b3bece35729)

| Property                 | InfoType                 | Cardinality |
|--------------------------|--------------------------|-------------|
| applicableStandard       | applicableStandard       | 1           |
| testID                   | testID                   | 1           |
| specifiedTemperature     | specifiedTemperature     | 1           |
| initialStress            | initialStress            | 1           |
| testDuration             | testDuration             | 1           |
| percentageCreepExtension | percentageCreepExtension | 1           |
| SingleCrystalOrientation | SingleCrystalOrientation | 1           |
| hasData                  | hasData                  | 1..n        |
| hasMetadata              | hasMetadata              | 1..n        |
| usesMaterial             | usesMaterial             | 1..n        |

### Material

**PID**: `21.T11969/d8169782b57c7a9e9f01`
**Local File**: [`Material.json`](profiles/Material.json)
**DTR Entry**: [View](https://typeregistry.lab.pidconsortium.net/objects/21.T11969/d8169782b57c7a9e9f01)

| Property               | InfoType               | Cardinality |
|------------------------|------------------------|-------------|
| materialID             | materialID             | 1           |
| previewImage           | previewImage           | 0..n        |
| semImage               | semImage               | 0..1        |
| hasChemicalComposition | hasChemicalComposition | 1           |
| hasHeatTreatment       | hasHeatTreatment       | 0..1        |

---

## Registration Status Summary

| Category         | Total  | Registered | Pending |
|------------------|--------|------------|---------|
| MeasurementUnits | 1      | 1          | 0       |
| BasicInfoTypes   | 7      | 7          | 0       |
| InfoTypes        | 45     | 45         | 0       |
| Profiles         | 8      | 8          | 0       |
| **Total**        | **61** | **61**     | **0**   |

---

## External References

### Standards
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