"""
Unit tests for src.main — Pure Core Pattern.

The blocking event loop is excluded via pragma: no cover.
All other branches are tested here with no real I/O.
"""

import pytest
import src.main as m


@pytest.mark.unit
class TestHandleSignal:
    def test_sets_running_false(self) -> None:
        original = m._running
        try:
            m._handle_signal(15, None)
            assert m._running is False
        finally:
            m._running = original

    def test_accepts_any_signum(self) -> None:
        original = m._running
        try:
            m._handle_signal(2, None)
            assert m._running is False
        finally:
            m._running = original


@pytest.mark.unit
class TestMain:
    def test_registers_signal_handlers(self, mocker: pytest.MonkeyPatch) -> None:
        mock_signal = mocker.patch("src.main.signal.signal")
        mocker.patch.object(m, "_running", False)
        m.main()
        assert mock_signal.call_count == 2

    def test_logs_startup_message(
        self, mocker: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        mocker.patch("src.main.signal.signal")
        mocker.patch.object(m, "_running", False)
        import logging

        with caplog.at_level(logging.INFO, logger="src.main"):
            m.main()
        assert any("Toy app starting" in r.message for r in caplog.records)
