import pytest


@pytest.fixture(autouse=True)
def enable_test_settings(settings):
    """
    Ensure Django knows when we run under pytest.

    - Sets settings.TESTING so the application can adjust behaviour
    - Can be extended with other global fixtures later
    """
    settings.TESTING = True

