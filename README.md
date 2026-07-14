[
![Docs](https://img.shields.io/badge/read-docs-success)
](https://maximiliani.github.io/fdo-usecases)
[
![Test Coverage](https://maximiliani.github.io/fdo-usecases/main/coverage_badge.svg)
](https://maximiliani.github.io/fdo-usecases/main/coverage)
[
![CI](https://img.shields.io/github/actions/workflow/status/maximiliani/fdo-usecases/ci.yml?branch=main&label=ci)
](https://github.com/maximiliani/fdo-usecases/actions/workflows/ci.yml)


<!-- --8<-- [start:abstract] -->
# fdo-usecases

A collection of FAIR Digital Object (FDO) usecases for materials science data management.

----

This repository implements practical applications of the FDO concept for managing
materials science experimental data. Each usecase demonstrates different aspects of
FDO creation, enrichment, and linking.

## Overview

This project provides:
- **LIS file parsing** for BAM creep test datasets
- **FDO generation** from Zenodo records
- **Materials science metadata extraction** following FAIR principles
- **Bidirectional linking** between experiments, materials, and publications

<!-- --8<-- [end:abstract] -->
<!-- --8<-- [start:quickstart] -->

## Installation

```bash
pip install git+ssh://git@github.com/maximiliani/fdo-usecases.git
```

## Getting Started

### Example: Parse BAM Creep Data

```python
import asyncio
from fdo_usecases.usecases.bam_creep_reference import LISParser
from fdo_usecases.designs.zenodo import ZenodoFDODesign

async def main():
    # Step 1: Fetch Zenodo records
    zenodo = ZenodoFDODesign(dois=["10.5281/zenodo.20132712"])
    await zenodo.execute_async()

    # Step 2: Parse LIS files
    async with LISParser() as parser:
        parser.load_from_zenodo_graph(zenodo._record_graph)

        # Get first test collection
        collections = parser.group_files_by_test_id()
        first_test = list(collections.keys())[0]

        # Parse metadata
        checksum = collections[first_test].md_tr_checksum
        metadata = await parser.parse_md_tr_file(checksum)

        print(f"Test: {metadata.test_id}")
        print(f"Material: {metadata.material_id}")
        print(f"Temperature: {metadata.specified_temperature}°C")
        print(f"Stress: {metadata.initial_stress} MPa")

asyncio.run(main())
```

### Run Complete Workflow

```bash
cd src/fdo_usecases/usecases/bam_creep_reference
python run.py
```

<!-- --8<-- [end:quickstart] -->

## Implemented Usecases

| Usecase | Description | Status |
|---------|-------------|--------|
| **[BAM Creep-Reference](src/fdo_usecases/usecases/bam_creep_reference/)** | Parse LIS files from BAM creep tests, create Material & Experiment FDOs | ✅ Complete |
| **[Zenodo FDO Generator](src/fdo_usecases/designs/zenodo/)** | Convert Zenodo records into FDO-compliant metadata graphs | ✅ Complete |

## Documentation

Detailed documentation available at: https://maximiliani.github.io/fdo-usecases

- [Developer Guide](docs/dev_guide.md)
- [API Reference](https://maximiliani.github.io/fdo-usecases/api)
- [Usecase Details](src/fdo_usecases/usecases/)

## Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=fdo_usecases

# Specific test module
pytest tests/usecases/bam_creep_reference/
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## Troubleshooting

### Common Issues

**Installation fails with `IndexError: list index out of range`**
Make sure you have `pip` > 21.2 (check with `pip --version`). Older versions have a bug causing this problem. Upgrade with:
```bash
pip install --upgrade pip
```

**Rate limiting when fetching files**
The HTTP client automatically handles rate limits with exponential backoff. Cached responses reduce repeated requests.

## License

Apache-2.0 - see [LICENSE](LICENSE) for details.

<!-- --8<-- [start:citation] -->

## How to Cite

If you want to cite this project in your scientific work,
please use the [citation file](https://citation-file-format.github.io/)
in the [repository](https://github.com/maximiliani/fdo-usecases/blob/main/CITATION.cff).

<!-- --8<-- [end:citation] -->
<!-- --8<-- [start:acknowledgements] -->

## Acknowledgements

We kindly thank all [authors and contributors](AUTHORS.md).

This work is funded by [TODO: Add funding information].

<!-- --8<-- [end:acknowledgements] -->
