# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Test Scrubber with DjangoIntegration.
"""

import pytest
from sentry_sdk.integrations.django import DjangoIntegration
from werkzeug.test import Client

from fillmore.scrubber import (
    build_scrub_cookies,
    build_scrub_query_string,
    Scrubber,
    Rule,
)
from tests.django.myapp.wsgi import application


INIT_KWARGS = {
    "auto_enabling_integrations": False,
    "integrations": [DjangoIntegration()],
}


@pytest.fixture
def client():
    return Client(application)


def test_scaffolding(sentry_helper, client):
    """Verifies the scaffolding for django integration tests is working"""
    with sentry_helper.init(**INIT_KWARGS) as sentry_client:
        resp = client.get("/broken")
        assert resp.status_code == 500

        # Enforces there's only one event and unpacks it
        (event,) = sentry_client.events

        assert "django" in event["sdk"]["integrations"]
        assert "request" in event


def test_scrub_request_headers(sentry_helper, client):
    """Test scrubbing headers"""
    scrubber = Scrubber(
        rules=[
            Rule(path="request.headers", keys=["Auth-Token"], scrub="scrub"),
        ],
    )
    kwargs = dict(INIT_KWARGS)
    kwargs["before_send"] = scrubber
    with sentry_helper.init(**kwargs) as sentry_client:
        resp = client.get("/broken", headers=[("Auth-Token", "abcde")])
        assert resp.status_code == 500

        # Enforces there's only one event and unpacks it
        (event,) = sentry_client.events

        assert event["request"]["headers"]["Auth-Token"] == "[Scrubbed]"
        assert event["request"]["headers"]["Host"] == "localhost"


def test_scrub_request_querystring(sentry_helper, client):
    """Test scrubbing querystring which is in the query_string field as a single string"""
    scrubber = Scrubber(
        rules=[
            Rule(
                path="request",
                keys=["query_string"],
                scrub=build_scrub_query_string(params=["code", "state"]),
            ),
        ],
    )
    kwargs = dict(INIT_KWARGS)
    kwargs["before_send"] = scrubber
    with sentry_helper.init(**kwargs) as sentry_client:
        resp = client.get(
            "/broken", query_string={"code": "foo", "state": "bar", "color": "pink"}
        )
        assert resp.status_code == 500

        # Enforces there's only one event and unpacks it
        (event,) = sentry_client.events

        query_string = list(sorted(event["request"]["query_string"].split("&")))
        assert query_string == [
            "code=%5BScrubbed%5D",
            "color=pink",
            "state=%5BScrubbed%5D",
        ]


def test_scrub_request_cookies(sentry_helper, client):
    """Test scrubbing cookies

    NOTE(willkg): Cookie data is only sent when send_default_pii=True and it
    gets sent in both the request.headers.Cookie field as well as the
    request.cookies field.

    """
    scrubber = Scrubber(
        rules=[
            Rule(
                path="request.headers",
                keys=["Cookie"],
                scrub=build_scrub_cookies(params=["csrftoken", "sessionid"]),
            ),
            Rule(
                path="request",
                keys=["cookies"],
                scrub=build_scrub_cookies(params=["csrftoken", "sessionid"]),
            ),
        ]
    )
    kwargs = dict(INIT_KWARGS)
    kwargs["send_default_pii"] = True
    kwargs["before_send"] = scrubber
    with sentry_helper.init(**kwargs) as sentry_client:
        # Add a bunch of cookies
        client.set_cookie(server_name="localhost", key="csrftoken", value="abcde")
        client.set_cookie(server_name="localhost", key="sessionid", value="someid")
        client.set_cookie(server_name="localhost", key="foo", value="bar")

        resp = client.get("/broken")
        assert resp.status_code == 500

        # Enforces there's only one event and unpacks it
        (event,) = sentry_client.events

        cookie_header = list(sorted(event["request"]["headers"]["Cookie"].split("; ")))
        assert cookie_header == [
            "csrftoken=[Scrubbed]",
            "foo=bar",
            "sessionid=[Scrubbed]",
        ]
        assert event["request"]["cookies"] == {
            "csrftoken": "[Scrubbed]",
            "foo": "bar",
            "sessionid": "[Scrubbed]",
        }
