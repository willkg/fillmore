# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest.mock import ANY

import pytest
import sentry_sdk
from sentry_sdk.integrations.stdlib import StdlibIntegration

from fillmore.scrubber import Scrubber, Rule
from fillmore.test import SentryTestHelper, get_sentry_base_url, diff_event


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


class Test_diff_event:
    @pytest.mark.parametrize(
        "a",
        [
            None,
            "",
            "abc",
            5,
            5.5,
            [1, 2, 3],
            {"a": "b"},
        ],
    )
    def test_basic_equals(self, a):
        assert diff_event(a, a) == []

    @pytest.mark.parametrize(
        "a, b",
        [
            (ANY, [1, 2, 3]),
            ([1, ANY, 3], [1, 2, 3]),
            (ANY, {"a": "b"}),
            ({"a": ANY}, {"a": [1, 2, 3]}),
        ],
    )
    def test_any(self, a, b):
        assert diff_event(a, b) == []
        assert diff_event(b, a) == []

    def test_different_types(self):
        assert diff_event(1, "a") == [
            {
                "a": 1,
                "b": "a",
                "path": "",
                "msg": "different types a:<class 'int'> b:<class 'str'>",
            }
        ]

    def test_deep(self):
        event = {
            "mechanism": {
                "handled": True,
                "type": "generic",
            },
            "stack": [
                {
                    "file": "some/path.py",
                    "in_app": True,
                    "line": 55,
                    "pre_context": "some string",
                },
                {
                    "file": "some/other/path.py",
                    "in_app": True,
                    "line": 42,
                    "pre_context": "some other string",
                },
            ],
            "modules": ["a", "b", "c"],
            "context": {
                "python": "3.9.12",
                "build": "42",
            },
        }
        expected_event = {
            "mechanism": None,
            "stack": [
                {
                    "file": "some/path.py",
                    "line": ANY,
                    "pre_context": ANY,
                    "meta": True,
                },
                {
                    "file": "some/other/path_elsewhere.py",
                    "line": ANY,
                    "pre_context": "some other string",
                    "meta": True,
                },
            ],
            "modules": ANY,
            "context": {
                "python": ANY,
                "build": ANY,
            },
        }

        differences = diff_event(event, expected_event)
        assert differences == [
            {
                "msg": "different types a:<class 'dict'> b:<class 'NoneType'>",
                "path": ".mechanism",
                "a": {"handled": True, "type": "generic"},
                "b": None,
            },
            {
                "msg": "in_app in a, not in b",
                "path": ".stack.[0]",
                "a": {
                    "file": "some/path.py",
                    "in_app": True,
                    "line": 55,
                    "pre_context": "some string",
                },
                "b": {
                    "file": "some/path.py",
                    "line": ANY,
                    "pre_context": ANY,
                    "meta": True,
                },
            },
            {
                "msg": "meta in b, not in a",
                "path": ".stack.[0]",
                "a": {
                    "file": "some/path.py",
                    "in_app": True,
                    "line": 55,
                    "pre_context": "some string",
                },
                "b": {
                    "file": "some/path.py",
                    "line": ANY,
                    "pre_context": ANY,
                    "meta": True,
                },
            },
            {
                "msg": "'some/other/path.py' != 'some/other/path_elsewhere.py'",
                "path": ".stack.[1].file",
                "a": "some/other/path.py",
                "b": "some/other/path_elsewhere.py",
            },
            {
                "msg": "in_app in a, not in b",
                "path": ".stack.[1]",
                "a": {
                    "file": "some/other/path.py",
                    "in_app": True,
                    "line": 42,
                    "pre_context": "some other string",
                },
                "b": {
                    "file": "some/other/path_elsewhere.py",
                    "line": ANY,
                    "pre_context": "some other string",
                    "meta": True,
                },
            },
            {
                "msg": "meta in b, not in a",
                "path": ".stack.[1]",
                "a": {
                    "file": "some/other/path.py",
                    "in_app": True,
                    "line": 42,
                    "pre_context": "some other string",
                },
                "b": {
                    "file": "some/other/path_elsewhere.py",
                    "line": ANY,
                    "pre_context": "some other string",
                    "meta": True,
                },
            },
        ]
