"""Tests for position lifecycle management."""

from __future__ import annotations

from trustdesk.orchestrator.lifecycle import (
    ExitReason,
    PositionMonitor,
    PositionState,
)


def _make_position(**overrides) -> PositionState:
    defaults = {
        "order_id": "ord-1",
        "pair": "BTC/USD",
        "side": "buy",
        "entry_price": 50000.0,
        "stop_loss": 48000.0,
        "tp1": 52000.0,
        "tp2": 55000.0,
        "opened_at": 1000.0,
    }
    defaults.update(overrides)
    return PositionState(**defaults)


class TestPositionMonitor:
    def test_track_and_get(self) -> None:
        monitor = PositionMonitor()
        pos = _make_position()
        monitor.track(pos)
        assert monitor.get("ord-1") is pos

    def test_get_unknown_returns_none(self) -> None:
        monitor = PositionMonitor()
        assert monitor.get("unknown") is None

    def test_open_positions(self) -> None:
        monitor = PositionMonitor()
        monitor.track(_make_position(order_id="a"))
        monitor.track(_make_position(order_id="b"))
        assert len(monitor.open_positions) == 2
        monitor.close("a", ExitReason.MANUAL)
        assert len(monitor.open_positions) == 1


class TestCheckExit:
    def test_no_exit_in_range(self) -> None:
        monitor = PositionMonitor(clock=lambda: 1100.0)
        monitor.track(_make_position())
        assert monitor.check_exit("ord-1", current_price=50500.0) is None

    def test_stop_loss_buy(self) -> None:
        monitor = PositionMonitor(clock=lambda: 1100.0)
        monitor.track(_make_position(side="buy", stop_loss=48000.0))
        assert monitor.check_exit("ord-1", current_price=47500.0) == ExitReason.STOP_LOSS

    def test_stop_loss_sell(self) -> None:
        monitor = PositionMonitor(clock=lambda: 1100.0)
        monitor.track(_make_position(side="sell", stop_loss=52000.0))
        assert monitor.check_exit("ord-1", current_price=52500.0) == ExitReason.STOP_LOSS

    def test_tp1_hit_buy(self) -> None:
        monitor = PositionMonitor(clock=lambda: 1100.0)
        monitor.track(_make_position(side="buy", tp1=52000.0, tp2=None))
        assert monitor.check_exit("ord-1", current_price=52500.0) == ExitReason.TP1_HIT

    def test_tp2_hit_buy(self) -> None:
        monitor = PositionMonitor(clock=lambda: 1100.0)
        monitor.track(_make_position(side="buy", tp1=52000.0, tp2=55000.0))
        assert monitor.check_exit("ord-1", current_price=56000.0) == ExitReason.TP2_HIT

    def test_time_exit(self) -> None:
        monitor = PositionMonitor(clock=lambda: 1000.0 + 86401.0)
        monitor.track(_make_position(opened_at=1000.0))
        assert monitor.check_exit("ord-1", current_price=50500.0) == ExitReason.TIME_EXIT

    def test_closed_position_returns_none(self) -> None:
        monitor = PositionMonitor(clock=lambda: 1100.0)
        monitor.track(_make_position())
        monitor.close("ord-1", ExitReason.MANUAL)
        assert monitor.check_exit("ord-1", current_price=47000.0) is None

    def test_unknown_order_id_returns_none(self) -> None:
        monitor = PositionMonitor(clock=lambda: 1100.0)
        assert monitor.check_exit("nonexistent", current_price=47000.0) is None

    def test_tp1_hit_sell(self) -> None:
        monitor = PositionMonitor(clock=lambda: 1100.0)
        monitor.track(_make_position(side="sell", tp1=48000.0, tp2=None))
        assert monitor.check_exit("ord-1", current_price=47500.0) == ExitReason.TP1_HIT

    def test_tp2_hit_sell(self) -> None:
        monitor = PositionMonitor(clock=lambda: 1100.0)
        monitor.track(_make_position(side="sell", tp1=48000.0, tp2=45000.0))
        assert monitor.check_exit("ord-1", current_price=44000.0) == ExitReason.TP2_HIT


class TestClose:
    def test_close_marks_position(self) -> None:
        monitor = PositionMonitor()
        monitor.track(_make_position())
        closed = monitor.close("ord-1", ExitReason.STOP_LOSS)
        assert closed is not None
        assert closed.closed is True
        assert closed.exit_reason == ExitReason.STOP_LOSS

    def test_close_unknown_returns_none(self) -> None:
        monitor = PositionMonitor()
        assert monitor.close("unknown", ExitReason.MANUAL) is None


class TestExitReason:
    def test_all_values_are_strings(self) -> None:
        for reason in ExitReason:
            assert isinstance(reason.value, str)

    def test_exit_reason_values(self) -> None:
        assert ExitReason.TP1_HIT == "tp1_hit"
        assert ExitReason.TP2_HIT == "tp2_hit"
        assert ExitReason.STOP_LOSS == "stop_loss"
        assert ExitReason.TIME_EXIT == "time_exit"
        assert ExitReason.INVALIDATION == "invalidation"
        assert ExitReason.MANUAL == "manual"
