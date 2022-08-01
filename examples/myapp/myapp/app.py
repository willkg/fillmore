# myapp/app.py
import logging
import logging.config

from fillmore.libsentry import set_up_sentry
from fillmore.scrubber import Scrubber, Rule, build_scrub_query_string


# Set up logging to capture fillmore error messages
logging.getLogger("fillmore").setLevel(logging.ERROR)

# Create a scrubber
scrubber = Scrubber(
    rules=[
        Rule(
            path="request.headers",
            keys=["Auth-Token", "Cookie"],
            scrub="scrub",
        ),
        Rule(
            path="request",
            keys=["query_string"],
            scrub=build_scrub_query_string(params=["code", "state"]),
        ),
        Rule(
            path="exception.values.[].stacktrace.frames.[].vars",
            keys=["username", "password"],
            scrub="scrub",
        ),
    ]
)

# Set up Sentry with the scrubber and the default integrations which
# includes the LoggingIntegration which will capture messages with level
# logging.ERROR.
set_up_sentry(
    sentry_dsn="http://user@example.com/1",
    host_id="some host id",
    release="some release name",
    before_send=scrubber,
)


def kick_up_exception():
    username = "James"  # noqa
    try:
        raise Exception("internal exception")
    except Exception:
        logging.getLogger(__name__).exception("kick_up_exception exception")
