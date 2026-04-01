"""Tests for chain adapter types."""
from __future__ import annotations

from trustdesk.adapters.chain.types import WritePriority, get_write_priority


class TestWritePriority:
    def test_enum_values(self) -> None:
        assert WritePriority.NORMAL.value == "normal"
        assert WritePriority.REDUCED.value == "reduced"
        assert WritePriority.CRITICAL.value == "critical"
        assert WritePriority.EMERGENCY.value == "emergency"


class TestGetWritePriority:
    def test_above_01_is_normal(self) -> None:
        assert get_write_priority(0.15) == WritePriority.NORMAL
        assert get_write_priority(1.0) == WritePriority.NORMAL

    def test_005_to_01_is_reduced(self) -> None:
        assert get_write_priority(0.1) == WritePriority.REDUCED
        assert get_write_priority(0.05) == WritePriority.REDUCED
        assert get_write_priority(0.07) == WritePriority.REDUCED

    def test_001_to_005_is_critical(self) -> None:
        assert get_write_priority(0.04) == WritePriority.CRITICAL
        assert get_write_priority(0.01) == WritePriority.CRITICAL

    def test_below_001_is_emergency(self) -> None:
        assert get_write_priority(0.009) == WritePriority.EMERGENCY
        assert get_write_priority(0.0) == WritePriority.EMERGENCY
