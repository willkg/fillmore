# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging

import pytest

from fillmore.scrubber import (
    build_scrub_cookies,
    build_scrub_query_string,
    _get_target_dicts,
    scrub,
    Scrubber,
    Rule,
)


@pytest.mark.parametrize(
    "value, expected",
    [
        # String values are scrubbed--this is straight-forward
        ("abc", "[Scrubbed]"),
        # Non-string values are also scrubbed--this can be problematic and engineers
        # setting up scrubbing should be thoughtful about what they're scrubbing
        (0, "[Scrubbed]"),
        ({"foo": "bar"}, "[Scrubbed]"),
    ],
)
def test_scrub(value, expected):
    assert scrub(value) == expected


@pytest.mark.parametrize(
    "cookies, keys, expected",
    [
        # Empty cookies variations: empty string, empty dict, empty list
        ("", [], ""),
        ({}, [], {}),
        ([], [], []),
        # Cover the variations of cookies as a string
        (
            "foo=bar; foo2=bar2",
            ["code", "state"],
            "foo=bar; foo2=bar2",
        ),
        (
            "code=abc123; state=base64string",
            ["code", "state"],
            "code=[Scrubbed]; state=[Scrubbed]",
        ),
        # If the cookies has nothing that needs scrubbing in it, then it returns the
        # cookies unaltered
        (
            "foo=bar;    foo2=bar2",
            ["code", "state"],
            "foo=bar;    foo2=bar2",
        ),
        # If the cookies has things that need scrubbing, then it will normalize
        # the cookies values.
        #
        # FIXME(willkg): This changes the cookies and will make debugging difficult, but
        # I don't see a better way to scrub without inadvertently fixing invalid things.
        (
            "code=abc123;    randomthing=value",
            ["code", "state"],
            "code=[Scrubbed]; randomthing=value",
        ),
        # Cover cookies as a dict
        (
            {"foo": "bar"},
            ["code", "state"],
            {"foo": "bar"},
        ),
        (
            {"code": "asdf", "foo": "bar"},
            ["code", "state"],
            {"code": "[Scrubbed]", "foo": "bar"},
        ),
        # Cover cookies as a list of tuples
        (
            [("foo", "bar")],
            ["code", "state"],
            [("foo", "bar")],
        ),
        (
            [("code", "asdf"), ("foo", "bar")],
            ["code", "state"],
            [("code", "[Scrubbed]"), ("foo", "bar")],
        ),
    ],
)
def test_scrub_cookies(cookies, keys, expected):
    scrub_fun = build_scrub_cookies(params=keys)
    assert scrub_fun(cookies) == expected


@pytest.mark.parametrize(
    "qs, keys, expected",
    [
        # Empty query_string variations: empty string, empty dict, empty list
        ("", [], ""),
        ({}, [], {}),
        ([], [], []),
        # Cover the variations of query_string as a string
        (
            "foo=bar&foo2=bar2",
            ["code", "state"],
            "foo=bar&foo2=bar2",
        ),
        (
            "code=abc123&state=base64String",
            ["code", "state"],
            "code=%5BScrubbed%5D&state=%5BScrubbed%5D",
        ),
        (
            "code=abc123&state",
            ["code", "state"],
            "code=%5BScrubbed%5D&state=%5BScrubbed%5D",
        ),
        # If the query_string has nothing that needs scrubbing in it, then
        # it returns the query_string unaltered
        (
            "test=%A&random&invalid_utf8=%A0%A1",
            ["code", "state"],
            "test=%A&random&invalid_utf8=%A0%A1",
        ),
        # If the query_string has things that need scrubbing, then it will normalize
        # the query_string values.
        #
        # FIXME(willkg): This changes the query_string and will make debugging difficult,
        # but I don't see a better way to scrub without inadvertently fixing invalid
        # things.
        (
            "code=55&test=%A&random&invalid_utf8=%A0%A1",
            ["code", "state"],
            "code=%5BScrubbed%5D&test=%25A&random=&invalid_utf8=%EF%BF%BD%EF%BF%BD",
        ),
        # Cover query_string as a dict
        (
            {"foo": "bar"},
            ["code", "state"],
            {"foo": "bar"},
        ),
        (
            {"code": "asdf", "foo": "bar"},
            ["code", "state"],
            {"code": "[Scrubbed]", "foo": "bar"},
        ),
        (
            {"foo": "bar", "state": ""},
            ["code", "state"],
            {"foo": "bar", "state": "[Scrubbed]"},
        ),
        # Cover query_string as a list of tuples
        (
            [("foo", "bar")],
            ["code", "state"],
            [("foo", "bar")],
        ),
        (
            [("code", "asdf"), ("foo", "bar")],
            ["code", "state"],
            [("code", "[Scrubbed]"), ("foo", "bar")],
        ),
        (
            [("foo", "bar"), ("state", "")],
            ["code", "state"],
            [("foo", "bar"), ("state", "[Scrubbed]")],
        ),
    ],
)
def test_scrub_query_string(qs, keys, expected):
    scrub_fun = build_scrub_query_string(params=keys)
    assert scrub_fun(qs) == expected


@pytest.mark.parametrize(
    "event, path, expected",
    [
        # Test empty things
        (
            {},
            [],
            [{}],
        ),
        # Test key traversal
        (
            {"foo": "bar"},
            [],
            [{"foo": "bar"}],
        ),
        (
            {"foo1": {"foo2": "bar"}},
            ["foo1"],
            [{"foo2": "bar"}],
        ),
        # Test [] array traversal
        (
            {
                "stack": {
                    "frames": [
                        {"index": 0, "values": {"code_id": "abcd"}},
                        {"index": 1, "values": {"state": "state_abcd"}},
                        {"index": 2, "values": {"code_id": "2_abcd"}},
                    ]
                }
            },
            ["stack", "frames", "[]", "values"],
            [
                {"code_id": "abcd"},
                {"state": "state_abcd"},
                {"code_id": "2_abcd"},
            ],
        ),
    ],
)
def test_get_target_paths(event, path, expected):
    assert list(_get_target_dicts(event, path)) == expected


@pytest.mark.parametrize(
    "event, path, expected",
    [
        # Test case where path points to item not in structure
        (
            {"exception": {"values": [{"foo": "bar"}]}},
            ["exception", "values", "[]", "stacktrace", "frames", "[]", "values"],
            [],
        )
    ],
)
def test_get_target_paths_missing(event, path, expected):
    assert list(_get_target_dicts(event, path)) == expected


class TestScrubber:
    @pytest.mark.parametrize(
        "rules, event, expected",
        [
            ([], {}, {}),
            (
                [Rule(path="foo", keys=["bar"], scrub=scrub)],
                {"foo": {"bar": "somevalue"}, "foo2": "othervalue"},
                {"foo": {"bar": "[Scrubbed]"}, "foo2": "othervalue"},
            ),
            (
                [Rule(path="foo", keys=["bar"], scrub="scrub")],
                {"foo": {"bar": "somevalue"}, "foo2": "othervalue"},
                {"foo": {"bar": "[Scrubbed]"}, "foo2": "othervalue"},
            ),
            (
                [
                    Rule(
                        path="frames.[].vars",
                        keys=["code_id", "state"],
                        scrub=scrub,
                    ),
                ],
                {
                    "frames": [
                        {"vars": {"foo": "bar"}},
                        {"vars": {"index": 4, "code_id": "abcd", "state": "def"}},
                    ],
                    "function": "somefunc",
                },
                {
                    "frames": [
                        {"vars": {"foo": "bar"}},
                        {
                            "vars": {
                                "index": 4,
                                "code_id": "[Scrubbed]",
                                "state": "[Scrubbed]",
                            }
                        },
                    ],
                    "function": "somefunc",
                },
            ),
            # Handle case where the parent isn't a dict so the key doesn't exist. This let's
            # us support a possible structure variation of request.data which could be a
            # data structure or a string.
            (
                [Rule(path="request.data", keys=["bar"], scrub=scrub)],
                {"request": {"data": "abcde"}},
                {"request": {"data": "abcde"}},
            ),
            (
                [Rule(path="request.data", keys=["bar"], scrub=scrub)],
                {"request": {"data": {"bar": "abcde"}}},
                {"request": {"data": {"bar": "[Scrubbed]"}}},
            ),
        ],
    )
    def test_scrubbing(self, rules, event, expected):
        scrubber = Scrubber(rules=rules)
        assert scrubber(event, {}) == expected

    def test_scrub_error(self, caplog):
        """Test scrub error when no error_handler is specified"""

        def bad_scrub(value):
            raise Exception("scruberror")

        event = {"request": {"data": {"foo": "bar"}}}

        scrubber = Scrubber(
            rules=[
                Rule(
                    path="request",
                    keys=["data"],
                    scrub=bad_scrub,
                )
            ]
        )
        scrubber(event, {})

        # The event should have ERROR WHEN SCRUBBING instead of [Scrubbed] or
        # something else
        assert event == {"request": {"data": "ERROR WHEN SCRUBBING"}}

        # A message should be logged at the ERROR level
        assert caplog.record_tuples == [
            (
                "fillmore.scrubber",
                logging.ERROR,
                "scrub fun error: bad_scrub, error: scruberror",
            )
        ]

    def test_scrub_error_error_handler(self, caplog):
        """Test scrub error when error_handler is specified"""

        class ErrorHandler:
            def __init__(self):
                self.errors = []

            def __call__(self, msg):
                self.errors.append(msg)

        handler = ErrorHandler()

        def bad_scrub(value):
            raise Exception("scruberror")

        event = {"request": {"data": {"foo": "bar"}}}

        scrubber = Scrubber(
            rules=[
                Rule(
                    path="request",
                    keys=["data"],
                    scrub=bad_scrub,
                )
            ],
            error_handler=handler,
        )
        scrubber(event, {})

        # The event should have ERROR WHEN SCRUBBING instead of [Scrubbed] or
        # something else
        assert event == {"request": {"data": "ERROR WHEN SCRUBBING"}}

        # error_handler was called with message
        assert handler.errors == ["scrub fun error: bad_scrub, error: scruberror"]

        # A message should be logged at the ERROR level
        assert caplog.record_tuples == [
            (
                "fillmore.scrubber",
                logging.ERROR,
                "scrub fun error: bad_scrub, error: scruberror",
            )
        ]

    def test_scrub_error_error_handler_error(self, caplog):
        """Test scrub error when error_handler is specified and error_handler kicks up error"""

        def bad_error_handler(msg):
            raise Exception("handlererror")

        def bad_scrub(value):
            raise Exception("scruberror")

        event = {"request": {"data": {"foo": "bar"}}}

        scrubber = Scrubber(
            rules=[
                Rule(
                    path="request",
                    keys=["data"],
                    scrub=bad_scrub,
                )
            ],
            error_handler=bad_error_handler,
        )
        scrubber(event, {})

        # The event should have ERROR WHEN SCRUBBING instead of [Scrubbed] or
        # something else
        assert event == {"request": {"data": "ERROR WHEN SCRUBBING"}}

        # Multiple messages should be logged at the ERROR level
        assert caplog.record_tuples == [
            (
                "fillmore.scrubber",
                logging.ERROR,
                "scrub fun error: bad_scrub, error: scruberror",
            ),
            (
                "fillmore.scrubber",
                logging.ERROR,
                "error in error_handler bad_error_handler",
            ),
        ]

    def test_path_error(self, caplog):
        """Test path error when error_handler is not specified"""

        event = {"request": {"data": {"foo": "bar"}}}

        scrubber = Scrubber(
            rules=[
                Rule(
                    path="request.[].data",
                    keys=["foo"],
                    scrub="scrub",
                )
            ],
        )
        scrubber(event, {})

        # The event isn't altered by rules with bad paths
        assert event == {"request": {"data": {"foo": "bar"}}}

        # Multiple messages should be logged at the ERROR level
        assert caplog.record_tuples == [
            (
                "fillmore.scrubber",
                logging.ERROR,
                "scrubber error: error: path 'request.[]' doesn't match event structure",
            ),
        ]

    def test_path_error_error_handler(self, caplog):
        """Test path error when error_handler is specified"""

        class ErrorHandler:
            def __init__(self):
                self.errors = []

            def __call__(self, msg):
                self.errors.append(msg)

        handler = ErrorHandler()

        event = {"request": {"data": {"foo": "bar"}}}

        scrubber = Scrubber(
            rules=[
                Rule(
                    path="request.[].data",
                    keys=["foo"],
                    scrub="scrub",
                )
            ],
            error_handler=handler,
        )
        scrubber(event, {})

        # The event isn't altered by rules with bad paths
        assert event == {"request": {"data": {"foo": "bar"}}}

        # error_handler was called with message
        assert handler.errors == [
            "scrubber error: error: path 'request.[]' doesn't match event structure"
        ]

        # Multiple messages should be logged at the ERROR level
        assert caplog.record_tuples == [
            (
                "fillmore.scrubber",
                logging.ERROR,
                "scrubber error: error: path 'request.[]' doesn't match event structure",
            ),
        ]

    def test_path_error_error_handler_error(self, caplog):
        """Test path error when error_handler is specified and errors"""

        def bad_error_handler(msg):
            raise Exception("handlererror")

        event = {"request": {"data": {"foo": "bar"}}}

        scrubber = Scrubber(
            rules=[
                Rule(
                    path="request.[].data",
                    keys=["foo"],
                    scrub="scrub",
                )
            ],
            error_handler=bad_error_handler,
        )
        scrubber(event, {})

        # The event isn't altered by rules with bad paths
        assert event == {"request": {"data": {"foo": "bar"}}}

        # Multiple messages should be logged at the ERROR level
        assert caplog.record_tuples == [
            (
                "fillmore.scrubber",
                logging.ERROR,
                "scrubber error: error: path 'request.[]' doesn't match event structure",
            ),
            ("fillmore.scrubber", 40, "error in error_handler bad_error_handler"),
        ]
