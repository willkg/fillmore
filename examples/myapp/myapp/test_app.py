# myapp/test_app.py
import unittest

from fillmore.test import SentryTestHelper

from myapp.app import kick_up_exception


class TestApp(unittest.TestCase):
    def test_scrubber(self):
        # Reuse the existing Sentry configuration and set up the helper
        # to capture Sentry events
        sentry_test_helper = SentryTestHelper()
        with sentry_test_helper.reuse() as sentry_client:
            kick_up_exception()

            (event,) = sentry_client.events
            error = event["exception"]["values"][0]
            self.assertEqual(error["type"], "Exception")
            self.assertEqual(error["value"], "internal exception")
            self.assertEqual(
                error["stacktrace"]["frames"][0]["vars"]["username"], "[Scrubbed]"
            )
