# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache2.0

"""Conditional utilities for FDO use cases.

This module provides helper functions for checking empty-ish values
and conditional evaluation.
"""

from typing import Any, Callable, TypeGuard


def is_emptyish(value: Any) -> bool:
    """Check if a value is "empty-ish".

    A value is considered empty-ish if it is None, an empty string, or a string
    that only contains whitespace.

    Args:
        value: The value to check.

    Returns:
        True if the value is empty-ish, False otherwise.

    """

    def is_list_any(value: object) -> TypeGuard[list[Any]]:
        return isinstance(value, list)

    def is_tuple_any(value: object) -> TypeGuard[tuple[Any, Any]]:
        return isinstance(value, tuple)

    isNone = value is None
    isEmptyArray = is_list_any(value) and len(value) <= 0
    isEmptyTuple = is_tuple_any(value) and len(value) <= 0
    isEmptyishString = isinstance(value, str) and value.strip().lower() in (
        "null",
        "",
        "()",
        "[]",
        "{}",
    )

    return isNone or isEmptyArray or isEmptyTuple or isEmptyishString


def otherwise(either: Callable[[], Any], otherwise: Callable[[], Any]) -> Any:
    """Return `either` if it is a valid value, otherwise execute and return `otherwise`.

    Args:
        either: The value to check.
        otherwise: The value to calculate and return if `either` is None.

    Returns:
        `either` if it is not None, otherwise `otherwise`.

    """
    eitherResult: Any = ""
    try:
        eitherResult = either()
    except Exception as e:
        print("    USE OTHER: First value in otherwise block threw exception: ", e)
        return otherwise()

    if isinstance(eitherResult, str) and eitherResult.strip().lower() in (
        "null",
        "",
        "()",
        "[]",
        "{}",
    ):
        eitherResult = None

    return eitherResult if not is_emptyish(eitherResult) else otherwise()


def stop_with_fail(message: str | None) -> None:
    if message is None or message == "":
        message = "No error message provided"
    raise Exception("Design stopped. " + message)
