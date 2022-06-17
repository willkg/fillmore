import json

import sentry_sdk

from francis.testing import SentryTestHelper


def test_capture_events():
    """Test the helper to make sure it's usable.

    NOTE(willkg): We use this helper in the francis tests, but we don't want to
    use our pytest fixture here.

    """
    helper = SentryTestHelper()
    with helper.session_context() as helper_with_context:
        helper_with_context.init()
        assert helper_with_context.events == []
        try:
            raise Exception("intentional")
        except Exception as exc:
            sentry_sdk.capture_exception(exc)

        (event,) = helper_with_context.events
        print(json.dumps(event, indent=2))
        assert event["exception"]["values"][0]["type"] == "Exception"
        assert event["exception"]["values"][0]["value"] == "intentional"

        try:
            raise Exception("another intentional")
        except Exception as exc:
            sentry_sdk.capture_exception(exc)

        (
            event1,
            event2,
        ) = helper_with_context.events
        assert event1["exception"]["values"][0]["type"] == "Exception"
        assert event1["exception"]["values"][0]["value"] == "intentional"

        assert event2["exception"]["values"][0]["type"] == "Exception"
        assert event2["exception"]["values"][0]["value"] == "another intentional"

    with helper.session_context() as helper_with_context:
        helper_with_context.init()
        assert helper_with_context.events == []
