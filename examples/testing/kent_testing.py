# examples/testing/kent_testing.py
import time

from fillmore.test import get_sentry_base_url, SentryTestHelper
import requests

# Use the werkzeug wsgi client because the Django test client fakes
# everything
from werkzeug.test import Client

from django.conf import settings

from myapp.wsgi import application


def test_sentry_with_kent():
    sentry_helper = SentryTestHelper()
    client = Client(application)
    kent_api = get_sentry_base_url(settings.SENTRY_DSN)

    # Flush the events from Kent and assert there are 0
    resp = requests.post(f"{kent_api}api/flush/")
    assert resp.status_code == 200
    resp = requests.get(f"{kent_api}api/errorlist/")
    assert len(resp.json()["errors"]) == 0

    # reuse uses an existing configured Sentry client, but mocks the
    # transport so you can assert things against the Sentry events
    # generated
    with sentry_helper.reuse():
        resp = client.get("/broken")
        assert resp.status_code == 500

        # Give sentry_sdk a chance to send the events to Kent
        time.sleep(1)

        # Get the event list and then the event itself
        resp = requests.get(f"{kent_api}api/errorlist/")
        event_data = resp.json()["errors"]
        assert len(event_data) == 1
        error_id = event_data[0]

        resp = requests.get(f"{kent_api}api/error/{error_id}")
        event = resp.json()["payload"]

        # Assert things against the event
        assert "django" in event["sdk"]["integrations"]
        assert "request" in event
        assert event["request"]["headers"]["Auth-Token"] == "[Scrubbed]"

        # FIXME: Assert that Fillmore didn't log any exceptions
