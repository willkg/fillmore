import pytest

from francis.test import SentryTestHelper


@pytest.fixture
def sentry_helper(request):
    """Returns a Sentry test helper"""
    return SentryTestHelper()
