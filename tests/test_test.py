# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest.mock import ANY

import json
import pytest
import sentry_sdk
from sentry_sdk.integrations.stdlib import StdlibIntegration

from fillmore.scrubber import Scrubber, Rule
from fillmore.test import (
    diff_structure,
    get_sentry_base_url,
    SaveEvents,
    SentryTestHelper,
)


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


def test_helper_capture_envelopes():
    """Test that helper captures envelopes."""
    helper = SentryTestHelper()
    with helper.init() as sentry_client:
        assert len(sentry_client.envelopes) == 0
        try:
            raise Exception("intentional")
        except Exception as exc:
            sentry_sdk.capture_exception(exc)

        assert len(sentry_client.envelopes) == 1
        (payload,) = sentry_client.envelope_payloads
        assert payload["exception"]["values"][0]["type"] == "Exception"
        assert payload["exception"]["values"][0]["value"] == "intentional"

        try:
            raise Exception("another intentional")
        except Exception as exc:
            sentry_sdk.capture_exception(exc)

        assert len(sentry_client.envelopes) == 2
        payload1, payload2 = sentry_client.envelope_payloads
        assert payload1["exception"]["values"][0]["type"] == "Exception"
        assert payload1["exception"]["values"][0]["value"] == "intentional"

        assert payload2["exception"]["values"][0]["type"] == "Exception"
        assert payload2["exception"]["values"][0]["value"] == "another intentional"


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
        assert len(sentry_client.envelopes) == 0

        sentry_sdk.capture_exception(Exception("intentional"))

        assert len(sentry_client.envelopes) == 1
        (payload,) = sentry_client.envelope_payloads
        assert payload["exception"]["values"][0]["type"] == "Exception"
        assert payload["exception"]["values"][0]["value"] == "intentional"

        sentry_sdk.capture_exception(Exception("another intentional"))

        assert len(sentry_client.envelopes) == 2
        payload1, payload2 = sentry_client.envelope_payloads
        assert payload1["exception"]["values"][0]["type"] == "Exception"
        assert payload1["exception"]["values"][0]["value"] == "intentional"

        assert payload2["exception"]["values"][0]["type"] == "Exception"
        assert payload2["exception"]["values"][0]["value"] == "another intentional"


def test_helper_contexts():
    """Test that new context clears envelopes."""
    helper = SentryTestHelper()
    with helper.init() as sentry_client:
        assert len(sentry_client.envelopes) == 0
        try:
            raise Exception("intentional")
        except Exception as exc:
            sentry_sdk.capture_exception(exc)

        assert len(sentry_client.envelopes) == 1
        (payload,) = sentry_client.envelope_payloads
        assert payload["exception"]["values"][0]["type"] == "Exception"
        assert payload["exception"]["values"][0]["value"] == "intentional"

    with helper.init() as sentry_client:
        assert len(sentry_client.envelopes) == 0


def test_helper_reset():
    """Test reset clears envelopes."""
    helper = SentryTestHelper()
    with helper.init() as sentry_client:
        assert len(sentry_client.envelopes) == 0
        try:
            raise Exception("intentional")
        except Exception as exc:
            sentry_sdk.capture_exception(exc)

        assert len(sentry_client.envelopes) == 1
        (payload,) = sentry_client.envelope_payloads
        assert payload["exception"]["values"][0]["type"] == "Exception"
        assert payload["exception"]["values"][0]["value"] == "intentional"

        sentry_client.reset()
        assert sentry_client.envelopes == []


def test_helper_reuse():
    helper = SentryTestHelper()

    with sentry_sdk.new_scope():
        # Initialize sentry
        sentry_sdk.init(
            dsn="http://user:pwd@localhost:8000/0",
            auto_enabling_integrations=False,
            default_integrations=False,
            integrations=[StdlibIntegration()],
        )

        # Reuse the sentry client we created which has an integration and
        # verify it still has integrations
        with helper.reuse() as reused_client:
            assert len(reused_client.envelopes) == 0
            try:
                raise Exception("intentional")
            except Exception as exc:
                sentry_sdk.capture_exception(exc)

            assert len(reused_client.envelopes) == 1
            (payload,) = reused_client.envelope_payloads
            assert payload["sdk"]["integrations"] == ["stdlib"]

        # Initialize a sentry with no integrations and verify it has no
        # integrations--this overwrites the global sentry
        kwargs = {
            "auto_enabling_integrations": False,
            "default_integrations": False,
            "integrations": [],
        }
        with helper.init(**kwargs) as sentry_client:
            assert len(sentry_client.envelopes) == 0
            try:
                raise Exception("intentional")
            except Exception as exc:
                sentry_sdk.capture_exception(exc)

            assert len(sentry_client.envelopes) == 1
            (payload,) = sentry_client.envelope_payloads
            assert payload["sdk"]["integrations"] == []

        # Reuse the newly initialized sentry with no integrations and verify there
        # are no integrations
        with helper.reuse() as reused_client:
            assert len(reused_client.envelopes) == 0
            try:
                raise Exception("intentional")
            except Exception as exc:
                sentry_sdk.capture_exception(exc)

            assert len(reused_client.envelopes) == 1
            (payload,) = reused_client.envelope_payloads
            assert payload["sdk"]["integrations"] == []


def test_capture_envelopes_with_scrubber():
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
        assert len(sentry_client.envelopes) == 0
        try:
            username = "foo"  # noqa
            raise Exception("intentional")
        except Exception as exc:
            sentry_sdk.capture_exception(exc)

        assert len(sentry_client.envelopes) == 1
        (payload,) = sentry_client.envelope_payloads
        error = payload["exception"]["values"][0]
        assert error["type"] == "Exception"
        assert error["value"] == "intentional"
        # Verify the username frame-local var is scrubbed
        assert error["stacktrace"]["frames"][0]["vars"]["username"] == "[Scrubbed]"


class Test_diff_structure:
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
        assert diff_structure(a, a) == []

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
        assert diff_structure(a, b) == []
        assert diff_structure(b, a) == []

    def test_different_types(self):
        assert diff_structure(1, "a") == [
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

        differences = diff_structure(event, expected_event)
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


def test_save_events(tmp_path):
    event_data = {"request": "data"}

    files = list(tmp_path.glob("*.json"))
    assert len(files) == 0

    scrubber = SaveEvents(wrapped_scrubber=Scrubber(rules=[]), outputdir=str(tmp_path))
    scrubber(event_data, {})

    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1

    with open(files[0], "r") as fp:
        data = json.load(fp)

    assert data == event_data
