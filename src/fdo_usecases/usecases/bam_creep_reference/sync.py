# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Compare an FDO graph against an Elasticsearch index and sync via the Typed PID Maker.

This module provides the building blocks and a high-level workflow to:

1. Load all FDO documents from a remote Elasticsearch index.
2. Compare them content-wise with a freshly built FDO graph.
3. Classify graph records as *new* (to create) or *changed* (to update).
4. Create new records via the Typed PID Maker batch endpoint.
5. Resolve placeholder (local) PIDs to real Handle PIDs in the updates.
6. Perform the updates and emit an Elasticsearch-ready export of the full graph.

Placeholder (local) PIDs are derived from the record content and prefixed
with ``PID_``, mirroring how the rest of the codebase computes record IDs:

- Grant FDOs: ``PID_grant:<funderRorId>::<grantCode>``
- File FDOs: ``PID_<checksum>``
- CreepExperiment FDOs: ``PID_<test ID>``
- Material FDOs: ``PID_<materialID>_<chemical-composition checksum>``
- Dataset/Publication FDOs: ``PID_<DOI>`` from the ``https://doi.org/`` landing page

The Elasticsearch index is treated as optional: if it is missing or empty the
comparison is skipped and every graph record is considered new.
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import aiohttp
from pytypid import SimpleRecord as ApiRecord
from pytypid_generated_client import ApiClient, Configuration, PIDManagementApi

from fdo_usecases.designer_lib.executor import from_placeholder, placeholder_pid
from fdo_usecases.designs.creep.constants import INFOTYPES as CREEP_INFOTYPES
from fdo_usecases.designs.grant.grant_design import INFOTYPES as GRANT_INFOTYPES
from fdo_usecases.designs.zenodo.constants import INFOTYPES as ZENODO_INFOTYPES

logger = logging.getLogger(__name__)

DEFAULT_TPM_HOST = "http://typed-pid-maker.datamanager.kit.edu/preview"

#: Default timeout (seconds) for Typed PID Maker requests. Batch creation
#: validates every record, which can take well over 30 minutes. Override with
#: the ``FDO_TPM_TIMEOUT_SECONDS`` environment variable.
TPM_REQUEST_TIMEOUT_SECONDS = int(os.environ.get("FDO_TPM_TIMEOUT_SECONDS", "3600"))


class Session(Protocol):
    """Minimal HTTP session interface (satisfied by ``aiohttp.ClientSession``)."""

    def post(self, url: str, **kwargs: Any) -> Any: ...

    def get(self, url: str, **kwargs: Any) -> Any: ...

    def put(self, url: str, **kwargs: Any) -> Any: ...


#: InfoType PIDs used to derive placeholder PIDs from record content.
_INFO_KEYS = {
    "checksum": ZENODO_INFOTYPES["checksum"],
    "landingPageLocation": ZENODO_INFOTYPES["landingPageLocation"],
    "testID": CREEP_INFOTYPES["testID"],
    "materialID": CREEP_INFOTYPES["materialID"],
    "hasChemicalComposition": CREEP_INFOTYPES["hasChemicalComposition"],
    "funderRorId": GRANT_INFOTYPES["funderRorId"],
    "grantCode": GRANT_INFOTYPES["grantCode"],
}

#: Kernel information profile type PID (special, not part of the local DTR).
_PROFILE_KEY = "21.T11148/076759916209e5d62bd5"

#: External InfoTypes used by the graphs but not registered in the local DTR.
_EXTERNAL_INFO_NAMES = {
    _PROFILE_KEY: "Kernel Information Profile",
    ZENODO_INFOTYPES["landingPageLocation"]: "landingPageLocation",
}


def _load_infotype_names() -> dict[str, str]:
    """Map InfoType/profile/basic-type PIDs to their human-readable names.

    Names are read from the local DTR type definitions under
    ``dtr/info_types``, ``dtr/profiles``, ``dtr/basic_info_types`` and
    ``dtr/measurement_units``. Types not registered locally fall back to a
    small set of known kernel/external types.

    Returns:
        Mapping from type PID to human-readable name.

    """
    names: dict[str, str] = {}
    dtr_dir = Path(__file__).resolve().parent / "dtr"
    for subdir in ("info_types", "profiles", "basic_info_types", "measurement_units"):
        for path in sorted((dtr_dir / subdir).glob("*.json")):
            try:
                with open(path, encoding="utf-8") as file:
                    data = json.load(file)
            except OSError:
                continue
            ident = data.get("Identifier")
            name = data.get("name")
            if ident and name:
                names.setdefault(ident, name)
    names.update(_EXTERNAL_INFO_NAMES)
    return names


#: Mapping from InfoType PID to human-readable name for the ES ingest export.
INFO_TYPE_NAMES = _load_infotype_names()


def _values(attrs: dict[str, Any], key: str) -> list[str]:
    """Return the string values stored under ``key`` in ``attrs``."""
    value = attrs.get(key)
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value]
    return [str(value)]


def _first(attrs: dict[str, Any], key: str) -> str | None:
    """Return the first string value stored under ``key`` in ``attrs``."""
    values = _values(attrs, key)
    return values[0] if values else None


def compute_placeholder(
    attrs: dict[str, Any],
    pid_map: dict[str, str] | None = None,
    include_material: bool = True,
) -> str | None:
    """Compute the placeholder (local) PID from record attributes.

    The rules are evaluated in a fixed order and mirror the record ID
    construction used by the record designs. ``pid_map`` (placeholder to real
    PID) is used to translate attribute values that have already been replaced
    by real Handle PIDs back to their placeholders, which is required for
    Material FDOs whose ``hasChemicalComposition`` value references a file.

    Args:
        attrs: Mapping of InfoType PID to a value or list of values.
        pid_map: Optional mapping from placeholder PIDs to real Handle PIDs.
        include_material: If True (default), also derive Material FDO
            placeholders. Set to False to only derive placeholders that do not
            depend on cross-record references.

    Returns:
        The placeholder PID, or None if it cannot be determined.

    """
    grant_code = _first(attrs, _INFO_KEYS["grantCode"])
    funder_id = _first(attrs, _INFO_KEYS["funderRorId"])
    if grant_code and funder_id:
        return placeholder_pid(f"grant:{funder_id}::{grant_code}")

    checksum = _first(attrs, _INFO_KEYS["checksum"])
    if checksum:
        return placeholder_pid(checksum)

    test_id = _first(attrs, _INFO_KEYS["testID"])
    if test_id:
        return placeholder_pid(test_id)

    for url in _values(attrs, _INFO_KEYS["landingPageLocation"]):
        if url.startswith("https://doi.org/"):
            return placeholder_pid(url[len("https://doi.org/") :])

    if include_material:
        material_id = _first(attrs, _INFO_KEYS["materialID"])
        chemical_composition = _first(attrs, _INFO_KEYS["hasChemicalComposition"])
        if material_id and chemical_composition:
            if pid_map:
                reverse = {real: placeholder for placeholder, real in pid_map.items()}
                chemical_composition = reverse.get(
                    chemical_composition, chemical_composition
                )
            return placeholder_pid(
                f"{material_id}_{from_placeholder(chemical_composition)}"
            )
    return None


def normalize_attrs(record: dict[str, Any]) -> dict[str, set[str]]:
    """Normalize a SimpleJSON record into an InfoType-PID to values mapping.

    Args:
        record: SimpleJSON record, i.e. ``{"pid": ..., "record": [{"key", "value"}]}``.

    Returns:
        Mapping of InfoType PID to the set of string values.

    """
    result: dict[str, set[str]] = {}
    for attr in record.get("record", []):
        result.setdefault(attr["key"], set()).add(str(attr["value"]))
    return result


def attrs_from_es_doc(doc: dict[str, Any]) -> dict[str, set[str]]:
    """Extract the attribute mapping from an Elasticsearch document.

    Documents follow the ingest layout ``{"pid": ..., "entries": {"<infoTypePID>":
    [{"key", "value", "name"}, ...]}}``. Only the ``value`` of each entry is
    kept. Values are coerced to strings so that numeric attributes stored by
    Elasticsearch compare equal to their JSON string representation.

    Args:
        doc: Elasticsearch document in the ``entries`` layout.

    Returns:
        Mapping of InfoType PID to the set of string values.

    """
    result: dict[str, set[str]] = {}
    entries = doc.get("entries")
    if not isinstance(entries, dict):
        return result
    for key, value in entries.items():
        values = value if isinstance(value, (list, tuple, set)) else [value]
        for item in values:
            if isinstance(item, dict):
                result.setdefault(key, set()).add(str(item.get("value", item)))
            else:
                result.setdefault(key, set()).add(str(item))
    return result


def resolve_placeholders(
    attrs: dict[str, set[str]],
    pid_map: dict[str, str],
    self_placeholder: str | None = None,
) -> dict[str, set[str]]:
    """Replace placeholder references with real PIDs in an attribute mapping.

    Values equal to ``self_placeholder`` are left untouched because some
    records carry literal attributes identical to their own placeholder PID
    (e.g. a file FDO whose ``checksum`` equals its own PID).

    Args:
        attrs: Mapping of InfoType PID to values.
        pid_map: Mapping from placeholder PIDs to real Handle PIDs.
        self_placeholder: Optional placeholder PID of the record itself.

    Returns:
        A new mapping with every known placeholder replaced by its real PID.

    """
    return {
        key: {
            value
            if self_placeholder is not None and value == self_placeholder
            else pid_map.get(value, value)
            for value in values
        }
        for key, values in attrs.items()
    }


def resolve_record_pids(
    record: dict[str, Any],
    pid_map: dict[str, str],
) -> dict[str, Any]:
    """Replace placeholder references with real PIDs in a SimpleJSON record.

    The ``pid`` field of the record is left untouched so the caller can decide
    whether it should keep its placeholder value (batch creation) or be
    replaced by the real PID (updates and exports). Literal attribute values
    that equal the record's own placeholder PID (e.g. a file's ``checksum``)
    are kept as-is.

    Args:
        record: SimpleJSON record.
        pid_map: Mapping from placeholder PIDs to real Handle PIDs.

    Returns:
        A new SimpleJSON record with all references resolved.

    """
    self_placeholder = record.get("pid")
    resolved_record = []
    for attr in record.get("record", []):
        value = attr["value"]
        if value != self_placeholder:
            value = pid_map.get(value, value)
        # Values are coerced to strings: the Typed PID Maker expects them as
        # such and references are looked up by their string placeholder.
        resolved_record.append({"key": attr["key"], "value": str(value)})
    return {"pid": record.get("pid"), "record": resolved_record}


@dataclass
class UpdateEntry:
    """A single change to an existing FDO."""

    placeholder: str
    real_pid: str
    record: dict[str, Any]
    changed_keys: list[str] = field(default_factory=list)
    diff: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the entry for reporting."""
        return {
            "placeholder": self.placeholder,
            "real_pid": self.real_pid,
            "changed_keys": self.changed_keys,
            "diff": self.diff,
            "record": self.record,
        }


@dataclass
class ComparisonResult:
    """Result of comparing a graph against an Elasticsearch index."""

    to_create: list[dict[str, Any]]
    to_update: list[UpdateEntry]
    unchanged: list[str]
    real_pid_by_placeholder: dict[str, str]


def compare_graph(
    graph_dict: dict[str, dict[str, Any]],
    es_docs: list[dict[str, Any]],
) -> ComparisonResult:
    """Classify graph records against the documents of an Elasticsearch index.

    Records whose placeholder PID is unknown to the index are new. Records
    whose attribute content (with placeholder references resolved to the real
    PIDs known from the index) differs from the stored document are updated.
    All other records are unchanged.

    Args:
        graph_dict: SimpleJSON graph keyed by placeholder PID.
        es_docs: Documents from the Elasticsearch index.

    Returns:
        The classification result.

    """
    es_by_placeholder = _index_es_docs(es_docs)
    real_pid_by_placeholder = {
        placeholder: doc["pid"] for placeholder, doc in es_by_placeholder.items()
    }

    to_create: list[dict[str, Any]] = []
    to_update: list[UpdateEntry] = []
    unchanged: list[str] = []

    for placeholder, record in graph_dict.items():
        expected = resolve_placeholders(
            normalize_attrs(record),
            real_pid_by_placeholder,
            self_placeholder=placeholder,
        )
        existing = es_by_placeholder.get(placeholder)
        if existing is None:
            to_create.append(record)
            continue
        real_pid, current = existing["pid"], attrs_from_es_doc(existing)
        changed_keys = sorted(
            key
            for key in set(expected) | set(current)
            if expected.get(key, set()) != current.get(key, set())
        )
        if not changed_keys:
            unchanged.append(placeholder)
            continue
        diff = [
            {
                "infoType": key,
                "current": sorted(current.get(key, set())),
                "expected": sorted(expected.get(key, set())),
            }
            for key in changed_keys
        ]
        to_update.append(UpdateEntry(placeholder, real_pid, record, changed_keys, diff))

    return ComparisonResult(to_create, to_update, unchanged, real_pid_by_placeholder)


def _index_es_docs(
    es_docs: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Index Elasticsearch documents by their computed placeholder PID.

    Basic placeholders (grants, files, experiments, datasets) are indexed
    first. Material placeholders depend on the chemical-composition file
    reference, so they are derived in a second pass once the file placeholder
    to real PID mapping is known.

    Args:
        es_docs: Documents from the Elasticsearch index.

    Returns:
        Mapping from placeholder PID to the corresponding index document.

    """
    index: dict[str, dict[str, Any]] = {}

    def add(placeholder: str, doc: dict[str, Any]) -> None:
        if placeholder in index:
            logger.warning(
                "Multiple Elasticsearch documents map to placeholder %s", placeholder
            )
        index[placeholder] = doc

    basic_index: dict[str, dict[str, Any]] = {}
    for doc in es_docs:
        pid = doc.get("pid")
        if not pid:
            logger.warning("Ignoring Elasticsearch document without pid field")
            continue
        placeholder = compute_placeholder(
            attrs_from_es_doc(doc), include_material=False
        )
        if placeholder:
            add(placeholder, doc)
            basic_index[placeholder] = doc
        else:
            logger.warning(
                "Cannot compute placeholder for Elasticsearch document with pid=%s",
                pid,
            )

    pid_map = {placeholder: doc["pid"] for placeholder, doc in index.items()}
    for doc in es_docs:
        placeholder = compute_placeholder(
            attrs_from_es_doc(doc), include_material=False
        )
        if placeholder in basic_index:
            continue
        placeholder = compute_placeholder(attrs_from_es_doc(doc), pid_map=pid_map)
        if placeholder:
            add(placeholder, doc)
    return index


def build_es_documents(
    graph_dict: dict[str, dict[str, Any]],
    pid_map: dict[str, str],
) -> list[dict[str, Any]]:
    """Serialize the finished graph for ingestion into Elasticsearch.

    Each document follows the index layout ``{"pid": ..., "entries":
    {"<infoTypePID>": [{"key", "value", "name"}, ...]}}`` with all placeholder
    references replaced by real Handle PIDs and a human-readable ``name`` for
    every InfoType.

    Args:
        graph_dict: SimpleJSON graph keyed by placeholder PID.
        pid_map: Mapping from placeholder PIDs to real Handle PIDs.

    Returns:
        List of Elasticsearch documents covering the full graph.

    """
    documents: list[dict[str, Any]] = []
    for placeholder, record in graph_dict.items():
        resolved = resolve_record_pids(record, pid_map)
        entries: dict[str, list[dict[str, str]]] = {}
        for attr in resolved["record"]:
            key = str(attr["key"])
            entries.setdefault(key, []).append(
                {
                    "key": key,
                    "value": str(attr["value"]),
                    "name": INFO_TYPE_NAMES.get(key, key),
                }
            )
        documents.append(
            {"pid": pid_map.get(placeholder, placeholder), "entries": entries}
        )
    return documents


async def fetch_index(
    session: Session,
    base_url: str,
    index: str,
    api_key: str | None = None,
    username: str | None = None,
    password: str | None = None,
) -> list[dict[str, Any]] | None:
    """Fetch all documents from an Elasticsearch index.

    Args:
        session: Shared aiohttp session.
        base_url: Elasticsearch base URL, e.g. ``https://host:9200``.
        index: Name of the index.
        api_key: Optional API key (``Authorization: ApiKey ...``).
        username: Optional username for basic authentication.
        password: Optional password for basic authentication.

    Returns:
        List of index documents, or None if the index is missing or empty.

    Raises:
        RuntimeError: On unexpected HTTP errors, e.g. authentication failures.

    """
    base = base_url.rstrip("/")
    headers = {"Authorization": f"ApiKey {api_key}"} if api_key else {}
    auth = None
    if username is not None and password is not None:
        auth = aiohttp.BasicAuth(username, password)

    def extract_hits(data: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            hit["_source"]
            for hit in data.get("hits", {}).get("hits", [])
            if "_source" in hit
        ]

    async with session.post(
        f"{base}/{index}/_search",
        headers=headers,
        auth=auth,
        json={
            "query": {"match_all": {}},
            "size": 1000,
            "scroll": "1m",
            "sort": ["_doc"],
        },
    ) as response:
        if response.status == 404:
            logger.info("ES index '%s' does not exist - ignoring comparison", index)
            return None
        if response.status >= 400:
            raise RuntimeError(
                f"ES search failed with status {response.status}: {(await response.text())[:500]}"
            )
        data = await response.json()

    documents = extract_hits(data)
    scroll_id = data.get("_scroll_id")
    while scroll_id:
        async with session.post(
            f"{base}/_search/scroll",
            headers=headers,
            auth=auth,
            json={"scroll": "1m", "scroll_id": scroll_id},
        ) as response:
            if response.status >= 400:
                raise RuntimeError(
                    f"ES scroll failed with status {response.status}: {(await response.text())[:500]}"
                )
            data = await response.json()
        scroll_id = data.get("_scroll_id")
        if not data.get("hits", {}).get("hits"):
            break
        documents.extend(extract_hits(data))

    if not documents:
        logger.info("ES index '%s' is empty - ignoring comparison", index)
        return None
    return documents


class TypedPidMaker:
    """Minimal client for the Typed PID Maker REST API.

    Batch creation reuses the generated ``pytypid`` client. Reading and updating
    single records uses raw HTTP because the generated client cannot address the
    wildcard ``/pid/**`` endpoints.
    """

    def __init__(self, host: str = DEFAULT_TPM_HOST, api_key: str | None = None):
        """Initialize the client.

        Args:
            host: Typed PID Maker base URL.
            api_key: Optional bearer token.

        """
        self._host = host.rstrip("/")
        self._api_key = api_key

    def _headers(self) -> dict[str, str]:
        if self._api_key:
            return {"Authorization": f"Bearer {self._api_key}"}
        return {}

    def create_bulk(self, records: list[dict[str, Any]]) -> dict[str, str]:
        """Create a batch of PID records.

        Args:
            records: SimpleJSON records with placeholder PIDs.

        Returns:
            Mapping from placeholder PIDs to the created Handle PIDs.

        Raises:
            RuntimeError: If the batch creation fails.

        """
        configuration = Configuration(host=self._host)
        if self._api_key:
            configuration.access_token = self._api_key
        graph_for_api = []
        for record in records:
            maybe_record = ApiRecord.from_dict(record)
            if maybe_record:
                graph_for_api.append(maybe_record.to_record())
        start = time.monotonic()
        with ApiClient(configuration) as api_client:
            api = PIDManagementApi(api_client)
            response = api.create_pids(
                pid_record=graph_for_api,
                dryrun=False,
                _request_timeout=TPM_REQUEST_TIMEOUT_SECONDS,
            )
        duration = time.monotonic() - start
        logger.info(
            "Typed PID Maker batch creation took %.1f seconds.",
            duration,
        )
        return dict(response.mapping or {})

    async def get_record(
        self,
        session: Session,
        pid: str,
    ) -> tuple[dict[str, Any], str]:
        """Fetch a PID record together with its current ETag.

        Args:
            session: Shared aiohttp session.
            pid: Real Handle PID of the record.

        Returns:
            Tuple of (SimplePidRecord body, ETag).

        Raises:
            RuntimeError: If the record cannot be fetched.

        """
        url = f"{self._host}/api/v1/pit/pid/{pid}"
        headers = {
            **self._headers(),
            "Accept": "application/vnd.datamanager.pid.simple+json",
        }
        timeout = aiohttp.ClientTimeout(total=TPM_REQUEST_TIMEOUT_SECONDS)
        async with session.get(url, headers=headers, timeout=timeout) as response:
            if response.status != 200:
                raise RuntimeError(f"GET {pid} failed with status {response.status}")
            body = await response.json()
            etag = response.headers.get("ETag") or response.headers.get("Etag") or ""
            if not etag:
                raise RuntimeError(f"GET {pid} returned no ETag")
            return body, etag

    async def update_record(
        self,
        session: Session,
        pid: str,
        etag: str,
        record: dict[str, Any],
    ) -> None:
        """Update a PID record using optimistic concurrency.

        Args:
            session: Shared aiohttp session.
            pid: Real Handle PID of the record.
            etag: Current ETag used for the ``If-Match`` header.
            record: SimplePidRecord body as it should be after the update.

        Raises:
            RuntimeError: If the update fails.

        """
        url = f"{self._host}/api/v1/pit/pid/{pid}"
        headers = {
            **self._headers(),
            "Content-Type": "application/vnd.datamanager.pid.simple+json",
            "Accept": "application/vnd.datamanager.pid.simple+json",
            "If-Match": etag,
        }
        timeout = aiohttp.ClientTimeout(total=TPM_REQUEST_TIMEOUT_SECONDS)
        async with session.put(
            url, headers=headers, json=record, timeout=timeout
        ) as response:
            if response.status not in (200, 201):
                raise RuntimeError(
                    f"PUT {pid} failed with status {response.status}: {(await response.text())[:500]}"
                )

    async def perform_updates(
        self,
        session: Session,
        updates: list[dict[str, Any]],
    ) -> None:
        """Perform a list of updates, retrying once on stale ETags.

        Args:
            session: Shared aiohttp session.
            updates: List of ``{"placeholder", "pid", "record"}`` dicts.

        """
        start = time.monotonic()
        for update in updates:
            pid = update["pid"]
            for attempt in range(2):
                try:
                    _, etag = await self.get_record(session, pid)
                    await self.update_record(session, pid, etag, update["record"])
                except RuntimeError as exc:
                    if attempt == 0:
                        logger.warning("Retrying update of %s: %s", pid, exc)
                        continue
                    logger.error("Failed to update %s: %s", pid, exc)
                    break
                else:
                    logger.info("Updated %s (%s)", update["placeholder"], pid)
                    break
        duration = time.monotonic() - start
        logger.info("Typed PID Maker updates took %.1f seconds.", duration)


def _write_json(path: Path, data: Any, description: str | None = None) -> None:
    """Write ``data`` as pretty JSON to ``path``.

    Args:
        path: Destination path for the JSON file.
        data: Data to serialize.
        description: Optional human-readable explanation of the artifact,
            logged together with the path.

    """
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
    if description:
        logger.info("Wrote %s - %s", path, description)
    else:
        logger.info("Wrote %s", path)


async def run_sync(
    graph_dict: dict[str, dict[str, Any]],
    es_base_url: str,
    es_index: str,
    output_dir: Path,
    tpm_host: str = DEFAULT_TPM_HOST,
    es_api_key: str | None = None,
    es_username: str | None = None,
    es_password: str | None = None,
    tpm_api_key: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Compare the graph against ES and create/update records in the Typed PID Maker.

    Emits the following artifacts into ``output_dir``:

    - ``bulk_create.json``: SimpleJSON records for the new FDOs.
    - ``updates.json``: The changes detected for existing FDOs.
    - ``mapping.json``: The placeholder-to-real-PID mapping (after creation).
    - ``updates_resolved.json``: The update payloads with fixed placeholder PIDs.
    - ``fdo_graph_es_ingest.json``: The full graph ready for ES ingestion, in the
      ``{"pid", "entries": {"<infoTypePID>": [{"key", "value", "name"}]}}`` layout.
    - ``sync_summary.json``: Counts and the placeholder-to-real-PID mapping.

    Args:
        graph_dict: SimpleJSON graph keyed by placeholder PID.
        es_base_url: Elasticsearch base URL.
        es_index: Elasticsearch index name.
        output_dir: Directory for the emitted JSON artifacts.
        tpm_host: Typed PID Maker base URL.
        es_api_key: Optional ES API key.
        es_username: Optional ES username.
        es_password: Optional ES password.
        tpm_api_key: Optional TPM bearer token.
        dry_run: If True, only emit JSON artifacts, do not call the TPM.

    Returns:
        Summary with counts and the placeholder-to-real-PID mapping.

    """
    output_dir = Path(output_dir)
    sync_start = time.monotonic()
    timeout = aiohttp.ClientTimeout(total=120)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        es_docs = await fetch_index(
            session,
            es_base_url,
            es_index,
            api_key=es_api_key,
            username=es_username,
            password=es_password,
        )
        if es_docs is None:
            logger.info(
                "Elasticsearch index '%s' is missing or empty - treating all %d "
                "graph records as new FDOs.",
                es_index,
                len(graph_dict),
            )
        else:
            logger.info(
                "Elasticsearch index '%s' contains %d FDO document(s).",
                es_index,
                len(es_docs),
            )

        result = compare_graph(graph_dict, es_docs or [])
        logger.info(
            "Comparison result: %d new, %d changed, %d unchanged of %d records.",
            len(result.to_create),
            len(result.to_update),
            len(result.unchanged),
            len(graph_dict),
        )
        logger.info(
            "Typed PID Maker at %s: %s.",
            tpm_host,
            "DRY-RUN, it will NOT be contacted"
            if dry_run
            else "will be used to create and update FDOs",
        )

        pid_map: dict[str, str] = dict(result.real_pid_by_placeholder)
        if pid_map:
            logger.info(
                "Resolved %d existing FDO(s) from the index to real Handle PIDs.",
                len(pid_map),
            )

        bulk_records = [
            resolve_record_pids(record, pid_map) for record in result.to_create
        ]
        _write_json(
            output_dir / "bulk_create.json",
            bulk_records,
            "payload for POST /api/v1/pit/pids (new FDOs, placeholder PIDs)",
        )
        _write_json(
            output_dir / "updates.json",
            [entry.to_dict() for entry in result.to_update],
            "changes detected for existing FDOs (before PID resolution)",
        )

        tpm = TypedPidMaker(host=tpm_host, api_key=tpm_api_key)

        created_mapping: dict[str, str] = {}
        if not dry_run and bulk_records:
            logger.info(
                "Sending %d new FDO record(s) to the Typed PID Maker batch "
                "endpoint (POST /api/v1/pit/pids).",
                len(bulk_records),
            )
            created = await asyncio.to_thread(tpm.create_bulk, bulk_records)
            created_mapping = created
            pid_map.update(created)
            logger.info(
                "Typed PID Maker created %d FDO(s) and returned their Handle PIDs.",
                len(created),
            )
            _write_json(
                output_dir / "mapping.json",
                pid_map,
                "placeholder PID -> real Handle PID mapping after creation",
            )
        elif bulk_records and dry_run:
            logger.info(
                "DRY-RUN: not creating %d new FDO(s) in the Typed PID Maker. "
                "Their placeholder PIDs stay unresolved.",
                len(bulk_records),
            )

        updates = []
        for entry in result.to_update:
            resolved = resolve_record_pids(entry.record, pid_map)
            resolved["pid"] = entry.real_pid
            updates.append(
                {
                    "placeholder": entry.placeholder,
                    "pid": entry.real_pid,
                    "record": resolved,
                }
            )
        _write_json(
            output_dir / "updates_resolved.json",
            updates,
            "update payloads with placeholder PIDs fixed to real Handle PIDs",
        )

        if not dry_run and updates:
            logger.info(
                "Performing %d update(s) in the Typed PID Maker (PUT "
                "/api/v1/pit/pid/{pid} with If-Match ETag).",
                len(updates),
            )
            await tpm.perform_updates(session, updates)
        elif updates and dry_run:
            logger.info(
                "DRY-RUN: not applying %d update(s) to the Typed PID Maker.",
                len(updates),
            )

        es_documents = build_es_documents(graph_dict, pid_map)
        _write_json(
            output_dir / "fdo_graph_es_ingest.json",
            es_documents,
            "full graph as ES documents with real Handle PIDs (for ingestion)",
        )

        summary = {
            "total": len(graph_dict),
            "to_create": len(result.to_create),
            "to_update": len(result.to_update),
            "unchanged": len(result.unchanged),
            "dry_run": dry_run,
            "created": len(created_mapping),
            "mapping": pid_map,
        }
        _write_json(
            output_dir / "sync_summary.json",
            summary,
            "machine-readable summary of this sync run",
        )

        if dry_run:
            logger.info(
                "DRY-RUN completed: the Typed PID Maker was NOT contacted. "
                "Re-run with FDO_SYNC_DRYRUN unset to actually create and "
                "update FDOs.",
            )
        else:
            logger.info(
                "Typed PID Maker involved: created %d, updated %d; %d unchanged.",
                len(created_mapping),
                len(updates),
                len(result.unchanged),
            )
        logger.info(
            "ES/TPM sync finished in %.1f seconds.",
            time.monotonic() - sync_start,
        )
        return summary


__all__ = [
    "ComparisonResult",
    "DEFAULT_TPM_HOST",
    "TypedPidMaker",
    "UpdateEntry",
    "attrs_from_es_doc",
    "build_es_documents",
    "compare_graph",
    "compute_placeholder",
    "fetch_index",
    "normalize_attrs",
    "resolve_placeholders",
    "resolve_record_pids",
    "run_sync",
]
