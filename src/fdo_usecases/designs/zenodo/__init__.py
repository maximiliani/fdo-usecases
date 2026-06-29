"""Zenodo-specific FDO designs.

This submodule contains design definitions for Zenodo-related FDOs.
"""

import asyncio
import json
import os

from fdo_usecases.designer_lib.executor import PidRecord
from fdo_usecases.designs.zenodo.design import ZenodoDesign


def create_fdo_graph(design: ZenodoDesign) -> dict[str, PidRecord]:
    """Create FDO records from Zenodo design without executing via Typed PID Maker.

    Args:
        design: ZenodoDesign instance

    Returns:
        Dictionary mapping record IDs to PidRecord objects

    """
    record_graph: dict[str, PidRecord] = {}
    dataset = asyncio.run(design._fetch_metadata())

    for version in dataset.versions.values():
        design._create_dataset_fdo(version, dataset)

        record_id = version.doi

        pid_record = PidRecord().setId(record_id).setPid("")

        for key, eval_funcs in design._attributes.items():
            for eval_func in eval_funcs:
                try:
                    value = eval_func()
                    pid_record.addAttribute(key, value)
                except Exception:  # noqa: S110
                    pass

        record_graph[record_id] = pid_record
        design._attributes.clear()
        design._backlinks.clear()

    design._create_file_fdos(dataset)

    for checksum, file_obj in dataset.all_files.items():
        if checksum not in record_graph:
            pid_record = PidRecord().setId(checksum).setPid("")

            pid_record.addAttribute(
                "21.T11148/076759916209e5d62bd5",
                "21.T11969/077fe9c54ed5ed26fa54",
            )
            pid_record.addAttribute(
                "21.T11148/076759916209e5d62bd5",
                "21.T11969/0738c2ef35faef0fb552",
            )
            pid_record.addAttribute("21.T11969/bd3e9fb9b606d2198c9e", file_obj.filename)
            if file_obj.mimetype:
                pid_record.addAttribute(
                    "21.T11969/3313b863118ed5eb0ded", file_obj.mimetype
                )
            pid_record.addAttribute(
                "21.T11969/479febb2bbe8400da547", str(file_obj.download_url)
            )
            pid_record.addAttribute("21.T11969/a80ed2ef79e22f1d8af8", file_obj.checksum)

            license_url = None
            for version_doi in file_obj.present_in_versions:
                if version_doi in dataset.versions:
                    version = dataset.versions[version_doi]
                    if version.license and version.license.url:
                        license_url = str(version.license.url)
                        break

            if license_url:
                pid_record.addAttribute("21.T11969/623654b1072ae7b88202", license_url)

            record_graph[checksum] = pid_record

    for rel in dataset.related_identifiers:
        identifier = rel.identifier
        if "zenodo" not in identifier.lower() and identifier not in record_graph:
            pid_record = PidRecord().setId(identifier).setPid("")
            pid_record.addAttribute(
                "21.T11148/076759916209e5d62bd5",
                "21.T11969/077fe9c54ed5ed26fa54",
            )
            pid_record.addAttribute(
                "21.T11148/076759916209e5d62bd5",
                "21.T11969/e00441c49bf6cb62a4a5",
            )
            pid_record.addAttribute("21.T11969/48e563f148dc04d8b31c", identifier)
            if rel.resource_type:
                pid_record.addAttribute(
                    "21.T11969/48dbf6a89f9748ae4ead", rel.resource_type
                )
            record_graph[identifier] = pid_record

    return record_graph


design = ZenodoDesign(doi="10.5281/zenodo.20132712")
fdo_graph = create_fdo_graph(design)

output_dir = os.path.dirname(os.path.abspath(__file__))
output_file = os.path.join(output_dir, "fdo_graph.json")

graph_dict = {}
for record_id, pid_record in fdo_graph.items():
    graph_dict[record_id] = pid_record.toSimpleJSON()

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(graph_dict, f, indent=2, ensure_ascii=False)

print(f"Saved FDO graph with {len(graph_dict)} records to {output_file}")
