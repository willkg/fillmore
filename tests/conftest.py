import pytest

from francis.testing import SentryTestHelper


@pytest.fixture
def sentry_helper(request):
    """Returns a Sentry test helper"""
    return SentryTestHelper()
