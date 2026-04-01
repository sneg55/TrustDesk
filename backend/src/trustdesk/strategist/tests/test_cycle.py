"""Tests for strategist cycle timing."""

from __future__ import annotations

from trustdesk.strategist.cycle import CycleTimer, get_cycle_interval


class TestGetCycleInterval:
    def test_trending_up_is_300(self) -> None:
        assert get_cycle_interval("TRENDING_UP") == 300

    def test_trending_down_is_900(self) -> None:
        assert get_cycle_interval("TRENDING_DOWN") == 900

    def test_ranging_is_300(self) -> None:
        assert get_cycle_interval("RANGING") == 300

    def test_volatile_is_120(self) -> None:
        assert get_cycle_interval("VOLATILE") == 120

    def test_unknown_regime_returns_default(self) -> None:
        assert get_cycle_interval("UNKNOWN") == 300


class TestCycleTimer:
    def test_first_call_should_run(self) -> None:
        timer = CycleTimer()
        assert timer.should_run("TRENDING_UP") is True

    def test_immediately_after_mark_should_not_run(self) -> None:
        current_time = 1000.0
        timer = CycleTimer(clock=lambda: current_time)
        timer.mark_run()
        assert timer.should_run("TRENDING_UP") is False

    def test_after_interval_should_run(self) -> None:
        times = iter([1000.0, 1301.0])
        timer = CycleTimer(clock=lambda: next(times))
        timer.mark_run()
        assert timer.should_run("TRENDING_UP") is True

    def test_volatile_shorter_interval(self) -> None:
        times = iter([1000.0, 1121.0])
        timer = CycleTimer(clock=lambda: next(times))
        timer.mark_run()
        assert timer.should_run("VOLATILE") is True

    def test_reset_makes_should_run_true(self) -> None:
        current_time = 1000.0
        timer = CycleTimer(clock=lambda: current_time)
        timer.mark_run()
        assert timer.should_run("TRENDING_UP") is False
        timer.reset()
        assert timer.should_run("TRENDING_UP") is True
