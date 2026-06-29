"""Example usage of Zenodo Metadata Extractor.

This script demonstrates how to fetch and explore dataset metadata from Zenodo,
including version tracking and file relationships.
"""

import asyncio
import sys

from zenodo_metadata_extractor import ZenodoAPIError, ZenodoDatasetFetcher


async def main():
    if len(sys.argv) > 1:
        doi = sys.argv[1]
    else:
        doi = "10.5281/zenodo.20132712"
        print(f"No DOI provided, using example: {doi}\n")

    fetcher = ZenodoDatasetFetcher(cache_enabled=True, timeout=30.0)

    try:
        dataset = await fetcher.fetch_by_doi(doi)
    except ZenodoAPIError as e:
        print(f"Error fetching dataset: {e}")
        sys.exit(1)

    print("=" * 80)
    print("DATASET OVERVIEW")
    print("=" * 80)
    print(f"Concept DOI: {dataset.concept_doi}")
    print(f"Concept Record ID: {dataset.concept_recid}")
    print(f"Title: {dataset.title}")
    if dataset.description:
        desc_preview = dataset.description[:200].replace("\n", " ").strip()
        print(f"Description: {desc_preview}...")
    print(f"Total versions: {len(dataset.versions)}")
    print(f"Total unique files: {len(dataset.all_files)}")
    print()

    print("=" * 80)
    print("VERSION HISTORY")
    print("=" * 80)

    latest = dataset.versions[dataset.latest_version_doi]

    versions_list = []
    current = latest
    while current:
        versions_list.append(current)
        current = current.previous_version

    versions_list.reverse()

    for _i, version in enumerate(versions_list):
        is_latest = version.doi == dataset.latest_version_doi
        marker = " [LATEST]" if is_latest else ""
        print(f"\nVersion {version.version_label}{marker}")
        print(f"  DOI: {version.doi}")
        print(f"  Record ID: {version.recid}")
        print(f"  Published: {version.publication_date}")
        print(f"  Files: {len(version.files)}")

        if version.creators:
            creator_names = [c.name for c in version.creators[:3]]
            if len(version.creators) > 3:
                creator_names.append(f"... and {len(version.creators) - 3} more")
            print(f"  Creators: {', '.join(creator_names)}")

        if version.license:
            print(f"  License: {version.license.id}")

    print("\n" + "=" * 80)
    print("FILE ANALYSIS")
    print("=" * 80)

    files_with_versions = [
        (checksum, f)
        for checksum, f in dataset.all_files.items()
        if len(f.present_in_versions) > 1
    ]

    print(f"\nFiles appearing in multiple versions: {len(files_with_versions)}")
    if files_with_versions:
        for checksum, file_obj in sorted(files_with_versions, key=lambda x: -x[1].size)[
            :10
        ]:
            print(f"\n  {file_obj.filename}")
            print(f"    Checksum: {checksum}")
            print(f"    Size: {file_obj.size:,} bytes")
            print(f"    First appeared: {file_obj.first_dataset_version}")
            print(f"    Present in: {', '.join(file_obj.present_in_versions)}")

    print("\n" + "=" * 80)
    print("FILE VERSION CHAINS (same name, different checksum)")
    print("=" * 80)

    chain_roots = [
        f
        for f in dataset.all_files.values()
        if f.previous_version is None and f.next_version is not None
    ]

    if chain_roots:
        print(f"\nFound {len(chain_roots)} file chains:\n")
        for root_file in chain_roots[:5]:
            print(f"File: {root_file.filename}")
            chain = [root_file]
            current = root_file.next_version
            while current:
                chain.append(current)
                current = current.next_version

            for i, file_ver in enumerate(chain):
                print(f"  v{i + 1}: {file_ver.filename}")
                print(f"       Checksum: {file_ver.checksum}")
                print(f"       Size: {file_ver.size:,} bytes")
                print(f"       First in: {file_ver.first_dataset_version}")
                if i < len(chain) - 1:
                    print("       ↓")
            print()
    else:
        print("\nNo file version chains found (all files have consistent checksums)")

    print("=" * 80)
    print("RELATED WORKS")
    print("=" * 80)

    if dataset.related_identifiers:
        for rel in dataset.related_identifiers:
            print(f"\n[{rel.relation}]")
            print(f"  Identifier: {rel.identifier}")
            print(f"  Type: {rel.resource_type or 'N/A'}")
            print(f"  Scheme: {rel.scheme or 'N/A'}")
    else:
        print("\nNo related identifiers found")

    print("\n" + "=" * 80)
    print("FUNDING")
    print("=" * 80)

    if dataset.grants:
        for grant in dataset.grants:
            print(f"\nGrant: {grant.code}")
            if grant.title:
                print(f"  Title: {grant.title}")
            if grant.funder_name:
                print(f"  Funder: {grant.funder_name}")
    else:
        print("\nNo funding information found")

    print("\n" + "=" * 80)
    print("COMMUNITIES")
    print("=" * 80)

    if dataset.communities:
        for comm in dataset.communities:
            print(f"  - {comm.id}")
    else:
        print("\nNo communities found")

    print("\n" + "=" * 80)
    print("DETAILED FILE LIST (Latest Version)")
    print("=" * 80)

    print(f"\nTotal files in latest version: {len(latest.files)}\n")

    sorted_files = sorted(latest.files.values(), key=lambda f: -f.size)

    for file_obj in sorted_files[:20]:
        size_kb = file_obj.size / 1024
        if size_kb > 1024:
            size_str = f"{size_kb / 1024:.1f} MB"
        else:
            size_str = f"{size_kb:.1f} KB"

        has_newer = "→ newer" if file_obj.next_version else ""
        has_older = "← older" if file_obj.previous_version else ""

        print(f"{file_obj.filename}")
        print(f"  {size_str} | {file_obj.checksum} {has_newer}{has_older}")

    if len(sorted_files) > 20:
        print(f"\n... and {len(sorted_files) - 20} more files")


if __name__ == "__main__":
    asyncio.run(main())
