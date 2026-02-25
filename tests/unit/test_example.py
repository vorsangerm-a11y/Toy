"""
Example unit test — demonstrates Pure Core Pattern.

Pure Core = business logic with NO I/O imports.
Tests are fast, isolated, no mocking needed.

Replace this with your actual unit tests.
"""
import pytest


class TestPureCoreExample:
    """Example unit tests for pure business logic."""

    def test_addition(self) -> None:
        """Example: pure function test — no mocking needed."""
        assert 1 + 1 == 2

    @pytest.mark.unit
    def test_string_manipulation(self) -> None:
        """Example: pure string logic test."""
        result = "hello world".title()
        assert result == "Hello World"
