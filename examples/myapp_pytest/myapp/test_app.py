# examples/myapp_pytest/myapp/test_app.py
from myapp.app import kick_up_exception


def test_scrubber(sentry_helper, caplog):
    # Reuse the existing Sentry configuration and set up the helper
    # to capture Sentry events
    with sentry_helper.reuse() as sentry_client:
        kick_up_exception()

        # Assert things against the Sentry event records
        (payload,) = sentry_client.envelope_payloads
        error = payload["exception"]["values"][0]
        assert error["type"] == "Exception"
        assert error["value"] == "internal exception"
        assert error["stacktrace"]["frames"][0]["vars"]["username"] == "[Scrubbed]"

        # Assert things against the logging messages created
        fillmore_records = [
            rec for rec in caplog.record_tuples if rec[0].startswith("fillmore")
        ]
        assert len(fillmore_records) == 0
