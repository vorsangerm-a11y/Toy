"""
Shared pytest fixtures.

Pure Core Pattern:
  - Unit tests use in-memory fakes (no I/O)
  - Integration tests use real DB via fixtures here
  - Behavioral tests use the running app

Add fixtures here that are shared across multiple test files.
"""

import pytest


# Example fixture — replace with your actual shared fixtures
@pytest.fixture
def sample_data() -> dict:
    """Shared sample data for tests."""
    return {"id": "test-123", "name": "Test Entity"}
