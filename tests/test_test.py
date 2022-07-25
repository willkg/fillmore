# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest
import sentry_sdk
from sentry_sdk.integrations.stdlib import StdlibIntegration

from fillmore.scrubber import Scrubber, Rule
from fillmore.test import SentryTestHelper, get_sentry_base_url


@pytest.mark.parametrize(
    "url, expected",
    [
        ("http://localhost/0", "http://localhost/"),
        ("http://localhost:8000/0", "http://localhost:8000/"),
        ("http://foo:bar@localhost:8000/0", "http://localhost:8000/"),
    ],
)
def test_get_sentry_base_url(url, expected):
    assert get_sentry_base_url(url) == expected


def test_helper_capture_events():
    """Test that helper captures events."""
    helper = SentryTestHelper()
    with helper.init() as sentry_client:
        assert sentry_client.events == []
        try:
            raise Exception("intentional")
        except Exception as exc:
            sentry_sdk.capture_exception(exc)

        (event,) = sentry_client.events
        assert event["exception"]["values"][0]["type"] == "Exception"
        assert event["exception"]["values"][0]["value"] == "intentional"

        try:
            raise Exception("another intentional")
        except Exception as exc:
            sentry_sdk.capture_exception(exc)

        (event1, event2) = sentry_client.events
        assert event1["exception"]["values"][0]["type"] == "Exception"
        assert event1["exception"]["values"][0]["value"] == "intentional"

        assert event2["exception"]["values"][0]["type"] == "Exception"
        assert event2["exception"]["values"][0]["value"] == "another intentional"


def test_helper_capture_exceptions_without_stack():
    scrubber = Scrubber(
        rules=[
            Rule(
                path="exception.values.[].stacktrace.frames.[].vars",
                keys=["username"],
                scrub="scrub",
            )
        ]
    )

    helper = SentryTestHelper()
    with helper.init(before_send=scrubber) as sentry_client:
        assert sentry_client.events == []

        sentry_sdk.capture_exception(Exception("intentional"))

        (event,) = sentry_client.events
        assert event["exception"]["values"][0]["type"] == "Exception"
        assert event["exception"]["values"][0]["value"] == "intentional"

        sentry_sdk.capture_exception(Exception("another intentional"))

        (event1, event2) = sentry_client.events
        assert event1["exception"]["values"][0]["type"] == "Exception"
        assert event1["exception"]["values"][0]["value"] == "intentional"

        assert event2["exception"]["values"][0]["type"] == "Exception"
        assert event2["exception"]["values"][0]["value"] == "another intentional"


def test_helper_contexts():
    """Test that new context clears events."""
    helper = SentryTestHelper()
    with helper.init() as sentry_client:
        assert sentry_client.events == []
        try:
            raise Exception("intentional")
        except Exception as exc:
            sentry_sdk.capture_exception(exc)

        (event,) = sentry_client.events
        assert event["exception"]["values"][0]["type"] == "Exception"
        assert event["exception"]["values"][0]["value"] == "intentional"

    with helper.init() as sentry_client:
        assert sentry_client.events == []


def test_helper_reset():
    """Test reset clears events."""
    helper = SentryTestHelper()
    with helper.init() as sentry_client:
        assert sentry_client.events == []
        try:
            raise Exception("intentional")
        except Exception as exc:
            sentry_sdk.capture_exception(exc)

        (event,) = sentry_client.events
        assert event["exception"]["values"][0]["type"] == "Exception"
        assert event["exception"]["values"][0]["value"] == "intentional"

        sentry_client.reset()
        assert sentry_client.events == []


def test_helper_reuse():
    helper = SentryTestHelper()

    with sentry_sdk.Hub(None):
        # Initialize sentry
        sentry_sdk.init(
            dsn="http://user:pwd@localhost:8000/0",
            auto_enabling_integrations=False,
            default_integrations=False,
            integrations=[StdlibIntegration()],
        )

        # Initialize a sentry with no integrations and verify it has no integrations
        kwargs = {
            "auto_enabling_integrations": False,
            "default_integrations": False,
            "integrations": [],
        }
        with helper.init(**kwargs) as sentry_client:
            assert sentry_client.events == []
            try:
                raise Exception("intentional")
            except Exception as exc:
                sentry_sdk.capture_exception(exc)

            (event,) = sentry_client.events
            assert event["sdk"]["integrations"] == []

        # Try reusing the sentry client we created already and verify it has integrations
        with helper.reuse() as reused_client:
            assert reused_client.events == []
            try:
                raise Exception("intentional")
            except Exception as exc:
                sentry_sdk.capture_exception(exc)

            (event,) = reused_client.events
            assert event["sdk"]["integrations"] == ["stdlib"]


def test_capture_events_with_scrubber():
    """Test the helper with scrubber."""
    scrubber = Scrubber(
        rules=[
            Rule(
                path="exception.values.[].stacktrace.frames.[].vars",
                keys=["username"],
                scrub="scrub",
            )
        ]
    )

    helper = SentryTestHelper()
    with helper.init(before_send=scrubber) as sentry_client:
        assert sentry_client.events == []
        try:
            username = "foo"  # noqa
            raise Exception("intentional")
        except Exception as exc:
            sentry_sdk.capture_exception(exc)

        (event,) = sentry_client.events
        error = event["exception"]["values"][0]
        assert error["type"] == "Exception"
        assert error["value"] == "intentional"
        # Verify the username frame-local var is scrubbed
        assert error["stacktrace"]["frames"][0]["vars"]["username"] == "[Scrubbed]"
