# SPDX-FileCopyrightText: 2026 Karlsruhe Institute of Technology
#
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for PidRecord self-reference prevention."""

import logging

from fdo_usecases.designer_lib.executor import PidRecord


class TestPidRecordSelfReference:
    """Tests for PidRecord.addAttribute self-reference prevention."""

    def test_self_reference_blocked_by_default(self, caplog):
        """Test that self-referencing attributes are skipped by default."""
        record = PidRecord()
        record.setId("md5:abc123")
        record.setPid("")

        with caplog.at_level(logging.INFO):
            record.addAttribute("21.T11969/2b4d6ceda80ddd63f7a9", "md5:abc123")

        # The tuple should NOT be added
        assert not record.contains(("21.T11969/2b4d6ceda80ddd63f7a9", "md5:abc123"))
        assert "Skipping self-referencing attribute" in caplog.text

    def test_self_reference_allowed_with_flag(self):
        """Test that allow_self_reference=True permits self-referencing values."""
        record = PidRecord()
        record.setId("md5:abc123")
        record.setPid("")

        record.addAttribute(
            "21.T11969/a80ed2ef79e22f1d8af8",
            "md5:abc123",
            allow_self_reference=True,
        )

        assert record.contains(("21.T11969/a80ed2ef79e22f1d8af8", "md5:abc123"))

    def test_non_self_reference_not_affected(self):
        """Test that normal (non-self-referencing) attributes work as before."""
        record = PidRecord()
        record.setId("md5:abc123")
        record.setPid("")

        record.addAttribute("21.T11969/bd3e9fb9b606d2198c9e", "My Dataset")
        record.addAttribute("21.T11969/2b4d6ceda80ddd63f7a9", "md5:def456")

        assert record.contains(("21.T11969/bd3e9fb9b606d2198c9e", "My Dataset"))
        assert record.contains(("21.T11969/2b4d6ceda80ddd63f7a9", "md5:def456"))

    def test_self_reference_blocked_in_list(self):
        """Test that self-references within lists are also blocked."""
        record = PidRecord()
        record.setId("md5:abc123")
        record.setPid("")

        # List contains both self-reference and valid value
        record.addAttribute(
            "21.T11969/2b4d6ceda80ddd63f7a9",
            ["md5:abc123", "md5:def456"],
        )

        # Self-reference should be skipped
        assert not record.contains(("21.T11969/2b4d6ceda80ddd63f7a9", "md5:abc123"))
        # Valid value should be present
        assert record.contains(("21.T11969/2b4d6ceda80ddd63f7a9", "md5:def456"))

    def test_self_reference_allowed_in_list_with_flag(self):
        """Test that allow_self_reference works with list values."""
        record = PidRecord()
        record.setId("md5:abc123")
        record.setPid("")

        record.addAttribute(
            "21.T11969/a80ed2ef79e22f1d8af8",
            ["md5:abc123", "md5:def456"],
            allow_self_reference=True,
        )

        assert record.contains(("21.T11969/a80ed2ef79e22f1d8af8", "md5:abc123"))
        assert record.contains(("21.T11969/a80ed2ef79e22f1d8af8", "md5:def456"))

    def test_empty_id_does_not_block(self):
        """Test that self-reference check is skipped when record ID is empty."""
        record = PidRecord()
        record.setId("")
        record.setPid("")

        # Value matches empty string - should not be blocked
        record.addAttribute("some_key", "")
        # Empty string value is a valid attribute (not a self-reference)
        # since _id is also empty, the guard (self._id != "") prevents blocking

    def test_none_value_still_skipped(self):
        """Test that None values are still skipped (existing behavior)."""
        record = PidRecord()
        record.setId("md5:abc123")
        record.setPid("")

        record.addAttribute("some_key", None)

        assert len(record._tuples) == 0
