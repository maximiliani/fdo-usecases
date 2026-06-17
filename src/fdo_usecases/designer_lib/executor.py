"""Executor for FDO record designs.

This module provides classes and functions for executing record designs,
processing JSON input files, and creating PIDs via the Typed PID Maker API.
"""

import json
import sys
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Self,
    Sequence,
    Set,
    Tuple,
    TypeVar,
)

from jsonpath import ExprSyntaxError, JSONPathTypeError
from pytypid import SimpleRecord as ApiRecord
from pytypid_generated_client import (
    ApiClient,
    BatchRecordResponse,
    Configuration,
    PIDManagementApi,
)
from pytypid_generated_client.models.pid_record import PIDRecord

from .conditionals import is_emptyish

Primitive = str | bool | int | float
# ---Types-for-designs------------------------------------------- #
JsonType = str | Sequence[Any] | Mapping[str, Any]
T = TypeVar("T")
Eval = Callable[[], T]
EvalPrimitive = Eval[str] | Eval[int] | Eval[float] | Eval[bool]


# ---Types-for-backlink-inference--------------------------------------- #
class Reaction:
    """Represents a reaction for backlink inference."""

    def __init__(self, receiver: str, backward_link_type: str) -> None:
        """Initialize a Reaction.

        Args:
            receiver: The receiver ID.
            backward_link_type: The type of backward link.

        """
        self.receiver = receiver
        self.backward_link_type = backward_link_type


# forward link-----v    v---receiver
Condition = Tuple[str, str]
InferenceRules = Dict[Condition, Reaction]


class BackwardLinkFor:
    """Marker class for backlink definitions."""

    def __init__(self, forward_link_type: str) -> None:
        """Initialize a BackwardLinkFor marker.

        Args:
            forward_link_type: The type of forward link.

        """
        self._forward_link_type = forward_link_type

    def get_forward_link_type(self) -> str:
        """Get the forward link type.

        Returns:
            The forward link type string.

        """
        return self._forward_link_type


# ---------------------------------------------------------------------  #


def log(value: Any, desc: Any) -> None:
    print(desc + ": " + value)


class CliInputProvider:
    """Provide input files from command line arguments.

    Example usage: python script.py file1.json my_files*.json
    """

    def __init__(self, args: List[str]) -> None:
        """Initialize the provider.

        Args:
            args: List of command line arguments.

        """
        self._args = args

    def nextInputFile(self) -> str | None:
        if not self._args:
            return None
        next_file = self._args.pop(0)
        if next_file.endswith(".json"):
            return next_file
        else:
            raise ValueError(f"Expected a JSON file, got: {next_file}")


class PidRecord:
    """Collect information about a single record and serialize it.

    Collects information about a single record and serializes it into a format
    for the Typed PID Maker.
    """

    def __init__(self) -> None:
        """Initialize an empty PidRecord."""
        self._id: str = ""
        self._pid: str = ""
        self._tuples: Set[Tuple[str, Primitive]] = set()

    def setPid(self, pid: str) -> Self:
        self._pid = pid
        return self

    def getPid(self) -> str:
        return self._pid

    def setId(self, id: str) -> Self:
        self._id = id
        return self

    def getId(self) -> str:
        return self._id

    def addAttribute(self, a: str, b: Primitive | List[Primitive] | None) -> Self:
        if b is None:
            return self
        if isinstance(b, List):
            for item in b:
                self.addAttribute(a, item)
            return self
        else:
            self._tuples.add((a, b))
        return self

    def contains(self, tuple: Tuple[str, Primitive]) -> bool:
        return tuple in self._tuples

    def toSimpleJSON(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "record": [{"key": key, "value": value} for (key, value) in self._tuples]
        }
        if self._pid and self._pid != "":
            result["pid"] = self._pid
        else:
            # if no pid is set, we use the id as pid,
            # so the Typed PID Maker can use the local identifier
            # to connect the different records
            result["pid"] = self._id
        return result


class RecordDesign:
    """Define how to build records from JSON data.

    With an API similar to PidRecord, this class collects information about how
    to build records given a JSON file and functions which extract information
    from the JSON file.

    Expects the JSON document to be globally available as "current_source_json".
    The given functions have to rely on this.
    """

    def __init__(self) -> None:
        """Initialize an empty RecordDesign."""
        self._id: Eval[str] = lambda: ""
        self._pid: Eval[str] = lambda: ""
        # key -> lambda: value
        self._attributes: Dict[str, List[Eval[Any]]] = dict()
        # Set of (forward_link_type, backward_link_type)
        self._backlinks: Set[Tuple[str, str]] = set()
        # If true, apply() shall skip the creation of a record.
        self._skipCondition: Eval[bool] = lambda: False

    def setId(self, id: Eval[str]) -> Self:
        self._id = id
        return self

    def setPid(self, pid: Eval[str]) -> Self:
        self._pid = pid
        return self

    def addAttribute(self, key: str, value: Eval[Any] | BackwardLinkFor) -> Self:
        if isinstance(value, BackwardLinkFor):
            self.addBacklink(value.get_forward_link_type(), key)
        else:
            if key not in self._attributes.keys():
                self._attributes[key] = [value]
            else:
                self._attributes[key].append(value)
        return self

    def setSkipCondition(self, condition: Eval[bool]) -> Self:
        self._skipCondition = condition
        return self

    def addBacklink(self, forward_link_type: str, backward_link_type: str) -> Self:
        self._backlinks.add((forward_link_type, backward_link_type))
        return self

    def apply(self, json: JsonType) -> Optional[Tuple[PidRecord, InferenceRules]]:
        """Apply the design to JSON data and return a PidRecord.

        Args:
            json: The JSON data to apply the design to.

        Returns:
            A tuple of (PidRecord, InferenceRules) if successful, None if skipped.

        """
        global current_source_json
        current_source_json = json

        if self._skipCondition():
            return None

        record: PidRecord = PidRecord()
        # errors regarding ID duplication and emptiness is in responsibility of the executer, not of the design
        record.setId(self._id())
        record.setPid(self._pid())

        for key, lazy_values in self._attributes.items():
            print("get", len(lazy_values), "potential values for attribute", key)
            for lazy_value in lazy_values:
                try:
                    value = lazy_value()
                    record.addAttribute(key, value)
                    print("    set value", value)
                except ExprSyntaxError as error:
                    print(
                        f"    ERROR: Can not retrieve value for {key}, because of JSONPath syntax error: {error}"
                    )
                    raise
                except JSONPathTypeError as error:
                    print(
                        f"    SKIP ATTRIBUTE: Can not retrieve value for {key}, because of JSONPath type error: {error}"
                    )

        rules: InferenceRules = {}
        for relation in self._backlinks:
            forward_link_type = relation[0]
            backward_link_type = relation[1]
            rules[forward_link_type, record.getId()] = Reaction(
                record.getId(), backward_link_type
            )
        return record, rules


"""
A function that executes a design must assign the current JSON to this global variable.
This is a workaround to allow the design to access the current JSON in any case the user
intends to use it. This is not a good practice, but it is the only way to allow users to
define their own functions that can access the current JSON. This is requied because
users may define functions and may use a "read from json" block in them. These blocks
are using this variable to refer to the current JSON.
"""
current_source_json: JsonType = "{}"


class Executor:
    """Execute record designs and create records from JSON input.

    This class processes input files, applies designs, and sends the resulting
    records to the Typed PID Maker API.
    """

    def __init__(self) -> None:
        """Initialize the Executor with empty state."""
        self.INPUT = CliInputProvider(sys.argv[1:])
        self.RECORD_DESIGNS: List[RecordDesign] = []
        self.RECORD_GRAPH: Dict[str, PidRecord] = {}
        # This is the place to store information about backlink inference from the records.
        #
        # Condition(forward_link_type, receiver_id) => Reaction(receiver_id, backward_link_type)
        self.INFERENCE_MATCHES_DB: InferenceRules = {}
        self.EXISTING_IDS: Set[str] = set()
        self.EXISTING_PIDS: Set[str] = set()

    def addDesign(self, design: RecordDesign) -> Self:
        """Add a design to the executor.

        Args:
            design: The RecordDesign to add.

        Returns:
            Self for method chaining.

        """
        self.RECORD_DESIGNS.append(design)
        return self

    def execute(self) -> Self:
        """Execute all designs on input files.

        Returns:
            Self for method chaining.

        """
        print("Amount of designs:", len(self.RECORD_DESIGNS))

        self._apply_inputs_to_designs()
        self._apply_inference_rules_to_records()
        self._send_graph_to_typed_pid_maker()
        return self

    def _send_graph_to_typed_pid_maker(self) -> None:
        """Send the record graph to the Typed PID Maker API.

        Creates PIDs for the records and stores the mapping from local IDs to real PIDs.
        """
        import os

        configuration = Configuration(
            host="http://typed-pid-maker.datamanager.kit.edu/preview"
        )

        with ApiClient(configuration) as api_client:
            api = PIDManagementApi(api_client)
            graph_for_api: List[PIDRecord] = []
            for record in self.RECORD_GRAPH.values():
                maybe_api_record = ApiRecord.from_dict(record.toSimpleJSON())
                if maybe_api_record:
                    graph_for_api.append(maybe_api_record.to_record())
            dryrun = False

            try:
                api_response: BatchRecordResponse = api.create_pids(
                    pid_record=graph_for_api, dryrun=dryrun
                )
                print("------ Successful response from API ---")

                # Define folder where we will store the mapping from local IDs to real PIDs
                # This is important information for updating the graph later on
                save_folder = os.path.dirname(os.path.abspath(__file__))
                if not len(graph_for_api) == len(self.RECORD_GRAPH) or (
                    api_response.mapping is not None
                    and not len(graph_for_api) == len(api_response.mapping)
                ):
                    print(
                        "Error: The number of records does not match the number of mappings."
                    )
                if api_response.mapping:
                    # save mapping to folder as "mappings.json"
                    with open(os.path.join(save_folder, "mappings.json"), "w") as f:
                        json.dump(api_response.mapping, f)
                else:
                    print("Error: No mapping received from API.")

                with open(os.path.join(save_folder, "api_response.json"), "w") as f:
                    json.dump(api_response.model_dump(by_alias=True), f, indent=2)
                    print(
                        "Saved mappings to", os.path.join(save_folder, "mappings.json")
                    )
                    print(
                        "Saved API response to",
                        os.path.join(save_folder, "api_response.json"),
                    )
                    print("Done.")
            except Exception as e:
                print("Exception when calling PIDManagementApi->create_pid: %s\n" % e)

    def _apply_inference_rules_to_records(self) -> None:
        for sender_id in self.RECORD_GRAPH:
            sender = self.RECORD_GRAPH[sender_id]
            matched_conditions = filter(
                lambda condition: sender.contains(condition),
                self.INFERENCE_MATCHES_DB.keys(),
            )
            reactions = map(
                lambda link: self.INFERENCE_MATCHES_DB[link], matched_conditions
            )
            for reaction in reactions:
                receiver: PidRecord = self.RECORD_GRAPH[reaction.receiver]
                receiver.addAttribute(reaction.backward_link_type, sender_id)

    def _apply_inputs_to_designs(self) -> None:
        """Apply input files to designs and create records.

        Generates records and inference rules which are stored in this class's state.
        """

        def assert_is_not_emptyish(value: Any, value_name: str) -> Any:
            if is_emptyish(value):
                raise ValueError(
                    f"{value_name} is empty or invalid. Record designs must have a non-empty, unique IDs. But was '{value}'."
                )
            return value

        def assert_uniqueness(
            value: Any, value_name: str, existing_values: Set[str]
        ) -> Any:
            if value in existing_values:
                raise ValueError(
                    f"{value_name} '{value}' is not unique. Record designs must have unique IDs. But this ID already exists in the graph."
                )
            return value

        for design in self.RECORD_DESIGNS:
            while True:
                input_file = self.INPUT.nextInputFile()
                if not input_file:
                    print("No more input files.")
                    break
                with open(input_file, "r") as file:
                    print("Processing input file", input_file)
                    json_data: JsonType = json.load(file)
                    assert len(json_data) > 0, "JSON file is empty or not valid."
                    sender: PidRecord
                    inference_rules: InferenceRules
                    maybe_record = design.apply(json_data)
                    if maybe_record is not None:
                        sender, inference_rules = maybe_record
                        print(f'Created record with ID: "{sender.getId()}"')

                        # ID checks
                        id = sender.getId()
                        assert_is_not_emptyish(id, "Record ID")
                        assert_uniqueness(id, "Record ID", self.EXISTING_IDS)
                        self.EXISTING_IDS.add(id)
                        # PID checks
                        pid = sender.getPid()
                        if not is_emptyish(pid):
                            assert_uniqueness(pid, "Record PID", self.EXISTING_PIDS)
                            self.EXISTING_PIDS.add(pid)
                        # Store the record in the graph
                        self.RECORD_GRAPH[sender.getId()] = sender
                        # merge rules into DB
                        self.INFERENCE_MATCHES_DB.update(inference_rules)
