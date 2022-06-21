import pytest

from francis.testing import SentryTestHelper


@pytest.fixture
def sentry_helper() -> SentryTestHelper:
    """SentryTestHelper fixture

    This creates a helper and sets up the context so it's usable immediately.

    """
    return SentryTestHelper()
