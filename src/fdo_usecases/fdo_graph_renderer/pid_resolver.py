# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""PID resolution for FDO graph renderer.

This module resolves attribute PIDs to human-readable names and descriptions
using local DTR files as primary source and handle.net as fallback.
"""

import logging
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class PIDResolver:
    """Resolves PIDs to metadata using local DTR files and network fallback."""

    def __init__(
        self,
        dtr_path: Optional[Path] = None,
        offline: bool = False,
        timeout: float = 5.0,
    ):
        """Initialize PID resolver.

        Args:
            dtr_path: Path to DTR JSON files directory. If None, auto-detects from input file location.
            offline: If True, skip network resolution entirely.
            timeout: Request timeout in seconds (default: 5.0).

        """
        self.dtr_path = dtr_path
        self.offline = offline
        self.timeout = timeout
        self.cache: dict[str, dict] = {}

        if dtr_path is not None:
            self._load_local_dtr(dtr_path)

    def _load_local_dtr(self, base_path: Path) -> None:
        """Load all JSON files from DTR directory structure.

        Scans info_types, profiles, and basic_info_types subdirectories.
        """
        subdirs = ["info_types", "profiles", "basic_info_types"]

        for subdir in subdirs:
            dir_path = base_path / subdir
            if not dir_path.exists():
                continue

            for json_file in dir_path.glob("*.json"):
                try:
                    import json

                    with open(json_file) as f:
                        data = json.load(f)

                    pid = data.get("Identifier")
                    if pid:
                        self.cache[pid] = {
                            "name": data.get("name", ""),
                            "description": data.get("description", ""),
                            "source": "local",
                        }
                except Exception as e:
                    logger.warning(f"Failed to load {json_file}: {e}")

    def resolve(self, pid: str) -> dict:
        """Resolve PID to name and description.

        Args:
            pid: The PID to resolve (e.g., "21.T11969/bd3e9fb9b606d2198c9e")

        Returns:
            Dictionary with 'name', 'description', and 'source' keys.
            Source can be 'local', 'network', or 'fallback'.

        """
        if pid in self.cache:
            return self.cache[pid]

        if self.offline:
            result = {"name": pid, "description": "", "source": "offline"}
            self.cache[pid] = result
            return result

        result = self._resolve_network(pid)
        self.cache[pid] = result
        return result

    def _resolve_network(self, pid: str) -> dict:
        """Resolve PID via handle.net redirect and API endpoint.

        Args:
            pid: The PID to resolve

        Returns:
            Dictionary with resolved metadata or fallback to PID

        """
        try:
            response = requests.get(
                f"https://hdl.handle.net/{pid}",
                allow_redirects=False,
                timeout=self.timeout,
            )

            if response.status_code == 302:
                redirect_url = response.headers.get("Location", "")
                api_url = redirect_url.replace("/#objects/", "/objects/")

                if api_url and api_url != redirect_url:
                    try:
                        metadata = requests.get(api_url, timeout=self.timeout).json()
                        return {
                            "name": metadata.get("name", pid),
                            "description": metadata.get("description", ""),
                            "source": "network",
                        }
                    except Exception as e:
                        logger.debug(f"Failed to fetch metadata from {api_url}: {e}")

        except requests.Timeout:
            logger.debug(f"Timeout resolving PID: {pid}")
        except requests.RequestException as e:
            logger.debug(f"Network error resolving PID {pid}: {e}")
        except Exception as e:
            logger.debug(f"Unexpected error resolving PID {pid}: {e}")

        return {"name": pid, "description": "", "source": "fallback"}

    def get_name(self, pid: str) -> str:
        """Get just the name for a PID.

        Convenience method that returns only the name field.
        """
        return self.resolve(pid)["name"]

    def get_description(self, pid: str) -> str:
        """Get just the description for a PID.

        Convenience method that returns only the description field.
        """
        return self.resolve(pid)["description"]
