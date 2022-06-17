import pytest

from francis.testing import SentryTestHelper


@pytest.fixture
def sentry_helper(request):
    """Returns a Sentry test helper"""
    helper = SentryTestHelper()
    with helper.session_context() as context:
        yield context
