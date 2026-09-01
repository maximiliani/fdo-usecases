# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for the Elasticsearch/Typed PID Maker sync module."""

import json
from pathlib import Path

import pytest

from fdo_usecases.designer_lib.executor import placeholder_pid
from fdo_usecases.designs.creep.constants import INFOTYPES as CREEP
from fdo_usecases.designs.grant.grant_design import INFOTYPES as GRANT
from fdo_usecases.designs.zenodo.constants import INFOTYPES as ZENODO
from fdo_usecases.usecases.bam_creep_reference.sync import (
    attrs_from_es_doc,
    build_es_documents,
    compare_graph,
    compute_placeholder,
    fetch_index,
    normalize_attrs,
    resolve_placeholders,
    resolve_record_pids,
)

MERGED_GRAPH = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "fdo_usecases"
    / "usecases"
    / "bam_creep_reference"
    / "fdo_graph_merged.json"
)


@pytest.fixture
def merged_graph() -> dict:
    """Load the committed merged FDO graph."""
    with open(MERGED_GRAPH, encoding="utf-8") as file:
        return json.load(file)


def test_compute_placeholder_reproduces_graph_keys(merged_graph):
    for key, record in merged_graph.items():
        assert compute_placeholder(normalize_attrs(record)) == key


def test_compute_placeholder_grant():
    attrs = {
        GRANT["grantCode"]: "460247524",
        GRANT["funderRorId"]: "https://ror.org/018mejw64",
    }
    assert (
        compute_placeholder(attrs) == "PID_grant:https://ror.org/018mejw64::460247524"
    )


def test_compute_placeholder_material_with_reverse_mapping():
    pid_map = {"PID_md5:chem": "21.T11148/900"}
    attrs = {
        CREEP["materialID"]: "CMSX-6",
        CREEP["hasChemicalComposition"]: "21.T11148/900",
    }
    assert compute_placeholder(attrs, pid_map) == "PID_CMSX-6_md5:chem"


def test_compute_placeholder_unknown_returns_none():
    assert compute_placeholder({}) is None
    assert compute_placeholder({ZENODO["keyword"]: "creep test"}) is None


def _es_doc(pid: str, entries: dict[str, list[str]]) -> dict[str, object]:
    """Build an ES document in the ``entries`` ingest layout."""
    return {
        "pid": pid,
        "entries": {
            key: [{"key": key, "value": value, "name": key} for value in values]
            for key, values in entries.items()
        },
    }


def test_attrs_from_es_doc_coerces_numbers_and_lists():
    doc = _es_doc(
        "21.T11148/1",
        {
            CREEP["initialStress"]: ["230.0", "230.0"],
            ZENODO["keyword"]: ["a"],
        },
    )
    attrs = attrs_from_es_doc(doc)
    assert attrs[CREEP["initialStress"]] == {"230.0"}
    assert attrs[ZENODO["keyword"]] == {"a"}
    assert "pid" not in attrs


def test_attrs_from_es_doc_ignores_missing_entries():
    assert attrs_from_es_doc({"pid": "21.T11148/1"}) == {}
    assert attrs_from_es_doc({}) == {}


def test_resolve_placeholders_and_record():
    pid_map = {"PID_md5:abc": "21.T11148/100", "PID_10.5281/zenodo.1": "21.T11148/200"}
    attrs = {ZENODO["hasPart"]: {"PID_md5:abc"}, ZENODO["keyword"]: {"data"}}
    assert resolve_placeholders(attrs, pid_map) == {
        ZENODO["hasPart"]: {"21.T11148/100"},
        ZENODO["keyword"]: {"data"},
    }
    record = {
        "pid": "PID_10.5281/zenodo.1",
        "record": [
            {"key": ZENODO["hasPart"], "value": "PID_md5:abc"},
            {"key": ZENODO["keyword"], "value": "data"},
        ],
    }
    assert resolve_record_pids(record, pid_map) == {
        "pid": "PID_10.5281/zenodo.1",
        "record": [
            {"key": ZENODO["hasPart"], "value": "21.T11148/100"},
            {"key": ZENODO["keyword"], "value": "data"},
        ],
    }


def _file_record(checksum="md5:abc", name="a.LIS"):
    return {
        "pid": placeholder_pid(checksum),
        "record": [
            {"key": ZENODO["checksum"], "value": checksum},
            {"key": ZENODO["name"], "value": name},
            {"key": ZENODO["keyword"], "value": "file"},
        ],
    }


def _dataset_record(doi="10.5281/zenodo.1", title="My Dataset", extra=None):
    record = {
        "pid": placeholder_pid(doi),
        "record": [
            {"key": ZENODO["landingPageLocation"], "value": f"https://doi.org/{doi}"},
            {"key": ZENODO["name"], "value": title},
            {"key": ZENODO["hasPart"], "value": "PID_md5:abc"},
            {"key": ZENODO["keyword"], "value": "dataset"},
        ],
    }
    if extra:
        record["record"].extend(extra)
    return record


def test_compare_graph_classification():
    graph = {
        "PID_md5:abc": _file_record(),
        "PID_10.5281/zenodo.1": _dataset_record(),
        "PID_Vh5205_C-89": {
            "pid": "PID_Vh5205_C-89",
            "record": [{"key": CREEP["testID"], "value": "Vh5205_C-89"}],
        },
    }
    es_docs = [
        _es_doc(
            "21.T11148/100",
            {
                ZENODO["checksum"]: ["md5:abc"],
                ZENODO["name"]: ["a.LIS"],
                ZENODO["keyword"]: ["file"],
            },
        ),
        _es_doc(
            "21.T11148/200",
            {
                ZENODO["landingPageLocation"]: ["https://doi.org/10.5281/zenodo.1"],
                ZENODO["name"]: ["My Dataset"],
                ZENODO["hasPart"]: ["21.T11148/100"],
                ZENODO["keyword"]: ["dataset"],
            },
        ),
    ]

    result = compare_graph(graph, es_docs)
    assert result.unchanged == ["PID_md5:abc", "PID_10.5281/zenodo.1"]
    assert result.to_create == [
        {
            "pid": "PID_Vh5205_C-89",
            "record": [{"key": CREEP["testID"], "value": "Vh5205_C-89"}],
        }
    ]
    assert result.real_pid_by_placeholder == {
        "PID_md5:abc": "21.T11148/100",
        "PID_10.5281/zenodo.1": "21.T11148/200",
    }
    assert result.to_update == []


def test_compare_graph_detects_changes():
    graph = {
        "PID_10.5281/zenodo.1": _dataset_record(title="Changed Title"),
        "PID_Vh5205_C-89": {
            "pid": "PID_Vh5205_C-89",
            "record": [{"key": CREEP["testID"], "value": "Vh5205_C-89"}],
        },
    }
    es_docs = [
        _es_doc(
            "21.T11148/200",
            {
                ZENODO["landingPageLocation"]: ["https://doi.org/10.5281/zenodo.1"],
                ZENODO["name"]: ["My Dataset"],
                ZENODO["hasPart"]: ["21.T11148/100"],
                ZENODO["keyword"]: ["dataset"],
            },
        )
    ]
    result = compare_graph(graph, es_docs)
    assert len(result.to_update) == 1
    entry = result.to_update[0]
    assert entry.placeholder == "PID_10.5281/zenodo.1"
    assert entry.real_pid == "21.T11148/200"
    assert ZENODO["name"] in entry.changed_keys
    assert result.to_create[0]["pid"] == "PID_Vh5205_C-89"


def test_compare_graph_empty_index_creates_all():
    graph = {"PID_md5:abc": _file_record()}
    result = compare_graph(graph, [])
    assert len(result.to_create) == 1
    assert result.real_pid_by_placeholder == {}


def test_build_es_documents(merged_graph):
    pid_map = {key: f"21.T11148/{index}" for index, key in enumerate(merged_graph)}
    documents = build_es_documents(merged_graph, pid_map)
    assert len(documents) == len(merged_graph)
    by_placeholder = {
        pid_map[key]: doc for key, doc in zip(merged_graph, documents, strict=False)
    }
    for key, doc in by_placeholder.items():
        assert doc["pid"] == key
        entries = doc["entries"]
        assert isinstance(entries, dict)
        assert entries
        for info_type, values in entries.items():
            assert isinstance(values, list) and values
            for entry in values:
                assert set(entry) == {"key", "value", "name"}
                assert entry["key"] == info_type
                assert isinstance(entry["value"], str)
                assert entry["name"]
    if ZENODO["checksum"] in next(iter(by_placeholder.values()))["entries"]:
        checksum_entries = next(iter(by_placeholder.values()))["entries"][
            ZENODO["checksum"]
        ]
        assert all(e["key"] == ZENODO["checksum"] for e in checksum_entries)


def test_compare_full_graph_against_derived_index(merged_graph):
    placeholders = list(merged_graph)
    pid_map = {key: f"21.T11148/{index}" for index, key in enumerate(placeholders)}
    es_docs = build_es_documents(merged_graph, pid_map)
    result = compare_graph(merged_graph, es_docs)
    assert result.to_create == []
    assert result.to_update == []
    assert result.unchanged == placeholders


@pytest.mark.asyncio
async def test_run_sync_dry_run_writes_artifacts(tmp_path, monkeypatch):
    import fdo_usecases.usecases.bam_creep_reference.sync as sync_mod

    graph = {
        "PID_md5:abc": _file_record(),
        "PID_10.5281/zenodo.1": _dataset_record(title="New Title"),
        "PID_Vh5205_C-89": {
            "pid": "PID_Vh5205_C-89",
            "record": [{"key": CREEP["testID"], "value": "Vh5205_C-89"}],
        },
    }
    es_docs = [
        _es_doc(
            "21.T11148/100",
            {
                ZENODO["checksum"]: ["md5:abc"],
                ZENODO["name"]: ["a.LIS"],
                ZENODO["keyword"]: ["file"],
            },
        ),
        _es_doc(
            "21.T11148/200",
            {
                ZENODO["landingPageLocation"]: ["https://doi.org/10.5281/zenodo.1"],
                ZENODO["name"]: ["My Dataset"],
                ZENODO["hasPart"]: ["21.T11148/100"],
                ZENODO["keyword"]: ["dataset"],
            },
        ),
    ]

    async def fake_fetch(session, *args, **kwargs):
        return es_docs

    monkeypatch.setattr(sync_mod, "fetch_index", fake_fetch)
    calls = []

    class FakeTPM:
        def __init__(self, *args, **kwargs):
            pass

        def create_bulk(self, records):
            calls.append(("create_bulk", records))
            return {}

    monkeypatch.setattr(sync_mod, "TypedPidMaker", FakeTPM)

    summary = await sync_mod.run_sync(
        graph_dict=graph,
        es_base_url="http://es",
        es_index="index",
        output_dir=tmp_path,
        dry_run=True,
    )

    assert calls == []
    assert summary["to_create"] == 1
    assert summary["to_update"] == 1
    assert summary["unchanged"] == 1
    for name in [
        "bulk_create.json",
        "updates.json",
        "updates_resolved.json",
        "fdo_graph_es_ingest.json",
        "sync_summary.json",
    ]:
        assert (tmp_path / name).exists()

    ingest = json.loads((tmp_path / "fdo_graph_es_ingest.json").read_text())
    assert {doc["pid"] for doc in ingest} == {
        "21.T11148/100",
        "21.T11148/200",
        "PID_Vh5205_C-89",
    }


class _FakeResponse:
    def __init__(self, status, json_data=None, text=""):
        self.status = status
        self.headers = {}
        self._json = json_data
        self._text = text

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def json(self):
        return self._json

    async def text(self):
        return self._text


class _FakeSession:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        response = self._responses.pop(0)
        if len(response) == 2:
            status, json_data = response
            return _FakeResponse(status, json_data)
        status, json_data, text = response
        return _FakeResponse(status, json_data, text)

    def get(self, url, **kwargs):
        raise NotImplementedError

    def put(self, url, **kwargs):
        raise NotImplementedError


@pytest.mark.asyncio
async def test_fetch_index_missing_returns_none():
    session = _FakeSession([(404, {})])
    assert await fetch_index(session, "http://es", "missing") is None
    assert session.calls[0][0] == "http://es/missing/_search"


@pytest.mark.asyncio
async def test_fetch_index_scrolls_and_returns_documents():
    search = {
        "_scroll_id": "scroll-1",
        "hits": {"hits": [{"_source": {"pid": "21.T11148/1"}}]},
    }
    empty = {"_scroll_id": "scroll-2", "hits": {"hits": []}}
    session = _FakeSession([(200, search), (200, empty)])
    docs = await fetch_index(session, "http://es", "index")
    assert docs == [{"pid": "21.T11148/1"}]
    assert session.calls[1][0] == "http://es/_search/scroll"


@pytest.mark.asyncio
async def test_fetch_index_empty_returns_none():
    session = _FakeSession([(200, {"hits": {"hits": []}})])
    assert await fetch_index(session, "http://es", "index") is None


@pytest.mark.asyncio
async def test_fetch_index_raises_on_auth_error():
    session = _FakeSession([(401, None, "unauthorized")])
    with pytest.raises(RuntimeError, match="401"):
        await fetch_index(session, "http://es", "index")
