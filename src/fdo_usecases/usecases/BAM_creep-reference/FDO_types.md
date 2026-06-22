# List of all PID-BasicInfoTypes, PID-InfoTypes, attributes, and profiles used in these FDO usecases

## PID-BasicInfoTypes (syntax definitions):
- [ ] [ORCiD]()
- [ ] [ROR]()
- [ ] [DOI]()
- [ ] [Handle]()
- [ ] [String]()
- [ ] [URL]()
- [ ] [SPDX_URL]()
- [ ] [ISO8601-DateTime]()
- [ ] [ISO8601-Duration]()
- [ ] [SemVerVersion]() -> vMajor.Minor.Fix
- [ ] [DecimalNumber]()
- [ ] [Percentage]() -> [0..1]
- [ ] [DecimalAngle]() -> [0..360]

## PID-InfoTypes (attributes):
- [ ] [kernelInformationProfile]() -> Handle 1..n
- [ ] [creatorAffiliation]() -> ROR 1..n
- [ ] [creator]() -> ORCiD 1..n
- [ ] [dateCreated]() -> ISO8601-DateTime 1
- [ ] [dateModified]() -> ISO8601-DateTime 0..1
- [ ] [helmholtzResearchArea]() -> String ["Health", "Information", "Earth & Environment", "Aeronautics, Space and Transport", "Energy", "Matter"] 1..n
- [ ] [helmholtzPoFStructure]() -> String 1..n
- [ ] [nfdiConsortia]() -> String 1..n
- [ ] [grantNumber]() -> String 1..n
- [ ] [keyword]() -> String 1..n
- [ ] [mimeType]() -> String 1
- [ ] [dataObjectLocation]() -> URL 1..n
- [ ] [spdxLicense]() -> SPDX_URL 1..n
- [ ] [dataCitePublicationType]() -> String 1 (see https://datacite-metadata-schema.readthedocs.io/en/4.7/properties/resourcetype/#a-resourcetypegeneral)
- [ ] [publisher]() -> String 1
- [ ] [datePublished]() -> ISO8601-DateTime 0..1
- [ ] [doi]() -> DOI 1
- [ ] [version]() -> SemVerVersion 1
- [ ] [nextVersion]() -> Handle 0..1
- [ ] [previousVersion]() -> Handle 0..1
- [ ] [latestVersion]() -> Handle 0..1
- [ ] [checksum]() -> String 1
- [ ] [previewImage]() -> URL 0..n
- [ ] [semImage]() -> Handle 0..1
- [ ] [hasChemicalComposition]() -> Handle 1
- [ ] [hasHeatTreatment]() -> Handle 0..1
- [ ] [hasData]() -> Handle 1..n
- [ ] [hasMetadata]() -> Handle 1..n
- [ ] [usesMaterial]() -> Handle 1..n
- [ ] [specifiedTemperature]() -> DecimalNumber 1
- [ ] [initialStress]() -> DecimalNumber 1
- [ ] [testDuration]() -> ISO8601-Duration 1
- [ ] [percentageCreepExtension]() -> Percentage 1
- [ ] [SingleCrystalOrientation]() -> DecimalAngle 1
- [ ] [applicableStandard]() -> String 1
- [ ] [testID]() -> String 1
- [ ] [materialID]() -> String 1
- [ ] [name]() -> String 1
- [ ] [description]() -> String 1

## Profiles:

### Base
- kernelInformationProfile
- creatorAffiliation
- creator
- dateCreated
- dateModified
- keyword
- name
- description

### Helmholtz
- helmholtzResearchArea
- helmholtzPoFStructure

## NFDI
- nfdiConsortia
- grantNumber

## Versionable
- version
- nextVersion
- previousVersion
- latestVersion

## DataResource
- mimeType
- dataObjectLocation
- spdxLicense
- checksum

## Publication
- doi
- dataCitePublicationType
- publisher
- datePublished
- creator

## CreepExperiment
- applicableStandard
- testID
- specifiedTemperature
- initialStress
- testDuration
- percentageCreepExtension
- SingleCrystalOrientation
- hasData
- hasMetadata
- usesMaterial

## Material
- materialID
- previewImage
- semImage
- hasChemicalComposition
- hasHeatTreatment