# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache2.0

"""File version chain building logic."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fdo_usecases.designs.zenodo.models import DatasetVersion, ZenodoFile


class FileChainBuilder:
    """Build file version chains across dataset versions."""

    def build_chains(
        self,
        all_files: dict[str, "ZenodoFile"],
        version_sequence: list["DatasetVersion"],
    ) -> None:
        """Link files with same name but different checksums across versions.

        This method establishes version chains for files that share the same filename
        but have different content (different checksums) across dataset versions.

        Algorithm:
        Step 1: Build Filename History - Group all files by filename
        Step 2: Create Bidirectional Links - Link consecutive versions chronologically

        Result:
        Files can be navigated like: v1 → v2 → v3 via next_version pointers
        And backward: v3 → v2 → v1 via previous_version pointers

        Args:
            all_files: Global registry of unique files (modified in-place)
            version_sequence: Chronologically ordered DatasetVersion list

        Example Chain:
            data.csv (v1.0, checksum A)
                ↓ next_version
            data.csv (v2.0, checksum B)
                ↓ next_version
            data.csv (v2.1, checksum C)

        """
        # Step 1: Build filename → [(version_index, checksum)] mapping
        filename_history: dict[str, list[tuple[int, str]]] = {}

        for version_idx, version in enumerate(version_sequence):
            for checksum, file_obj in version.files.items():
                if file_obj.filename not in filename_history:
                    filename_history[file_obj.filename] = []
                filename_history[file_obj.filename].append((version_idx, checksum))

        # Step 2: Create bidirectional links for each filename chain
        for occurrences in filename_history.values():
            # Skip files that only appear once (no versioning needed)
            if len(occurrences) <= 1:
                continue

            # Sort by version index to ensure chronological ordering
            sorted_occurrences = sorted(occurrences, key=lambda x: x[0])

            # Link consecutive versions
            for i in range(len(sorted_occurrences) - 1):
                _, checksum_current = sorted_occurrences[i]
                _, checksum_next = sorted_occurrences[i + 1]

                # Skip if checksums are identical (same file, no change)
                if checksum_current == checksum_next:
                    continue

                # Get file objects and establish bidirectional link
                file_current = all_files[checksum_current]
                file_next = all_files[checksum_next]

                # Set object references for metadata model navigation
                file_current.next_version = file_next
                file_next.previous_version = file_current

                # NEW: Also set checksum references for FDO creation
                file_current.next_version_checksum = file_next.checksum
                file_next.previous_version_checksum = file_current.checksum
