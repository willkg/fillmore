========
Fillmore
========

The Python sentry-sdk has a before_send hook that lets you scrub Sentry events
before they're sent. Fillmore makes it easier to set up a before_send scrubber
and test it.

:Code:          https://github.com/willkg/fillmore
:Issues:        https://github.com/willkg/fillmore/issues
:License:       MPL v2
:Documentation: https://fillmore.readthedocs.io/


Goals
=====

Goals of Fillmore:

1. make it easier to configure Sentry event scrubbing in a way that you can
   reason about
2. make it easier to test your scrubbing code so you know it's working over
   time
3. scrub in a resilient manner and default to emitting some signal when it
   kicks up errors so you know when your error handling code is kicking up
   errors

From that, Fillmore has the following features:

* lets you specify keys to scrub in a Sentry event
* resilient to errors--if it fails, it will emit a signal that you can see and
  alert on
* links to relevant Sentry documentation, projects, and other things
* testing infrastructure to use in your integration tests


Install
=======

Run::

    $ pip install fillmore


Quickstart
==========

Example::

    # Create a scrubber
    from fillmore.scrubber import Scrubber, ScrubRule, build_scrub_query_string

    scrubber = Scrubber(
        scrub_rules=[
            ScrubRule(
                key_path="request.headers",
                keys=["Auth-Token", "Cookie"],
                scrub_function="scrub",
            ),
            ScrubRule(
                key_path="request",
                keys=["query_string"],
                scrub_function=build_scrub_query_string(params=["code", "state"]),
            ),
            ScrubRule(
                key_path="exception.values.[].stacktrace.frames.[].vars",
                keys=["username", "password"],
                scrub_function="scrub",
            ),
        ]
    )

    # Set up Sentry with the scrubber
    sentry_sdk.init(
        sentry_dsn="somedsn",
        ...,
        before_send=scrubber,
    )


Now you've got a scrubber. However, how do you know it's scrubbing the right
stuff? How will you know if something changes and it's no longer scrubbing the
right stuff?

Fillmore comes with a test harness you can use. For example, say you have a
app called "myapp"::

    # myapp/libsentry.py
    import sentry_sdk

    # Create a scrubber
    from fillmore.scrubber import Scrubber, ScrubRule, build_scrub_query_string

    scrubber = Scrubber(
        scrub_rules=[
            ScrubRule(
                key_path="request.headers",
                keys=["Auth-Token", "Cookie"],
                scrub_function="scrub",
            ),
            ScrubRule(
                key_path="request",
                keys=["query_string"],
                scrub_function=build_scrub_query_string(params=["code", "state"]),
            ),
            ScrubRule(
                key_path="exception.values.[].stacktrace.frames.[].vars",
                keys=["username", "password"],
                scrub_function="scrub",
            ),
        ]
    )


Then you can test it like this::

    # myapp/tests/test_libsentry.py
    from myapp.libsentry import scrubber

    from fillmore.test import SentryTestHelper


    def test_scrubber():
        helper = SentryTestHelper()
        with helper.session_context() as helper_with_context:
            helper_with_context.init(scrubber=scrubber)

            try:
                username = "foo"
                raise Exception("intentional")
            except Exception as exc:
                sentry_sdk.capture_exception(exc)

            (event,) = helper_with_context.events
            error = event["exception"]["values"][0]
            assert error["type"] == "Exception"
            assert error["value"] == "intentional"
            assert error["stacktrace"]["frames"][0]["vars"]["username"] == "[Scrubbed]"


This kicks up an exception in this context which sentry captures. If you need
to test scrubbing for other contexts, you'll need to set that up differently.
See Fillmore documentation for details and recipes.


Why this? Why not other libraries?
==================================

Other libraries:

* **Have an awkward API that is hard to reason about.**

  I'm not scrubbing Sentry events for fun. I need to be able to write scrubbing
  configuration that is exceptionally clear about what it is and isn't doing.

* **Don't covers large portions of the Sentry event structure.**

  I need scrubbers that cover the entire event structure as well as some
  of the curious cases like the fact that cookie information shows up twice
  and can be encoded as a string.

* **Aren't resilient.**

  The scrubber is running in the context of Sentry reporting an error. If it
  also errors out, then you can end up in situations where you never see errors
  and have no signal that something is horribly wrong. We need scrubbing code
  to be extremely resilient and default to emitting a signal that it's broken.

* **Don't include testing infrastructure.**

  I'm not scrubbing Sentry events for fun. I need to know that the scrubbing
  code is working correctly and that it continues to work as we upgrade
  Python, sentry_sdk, and other things.

  Having testing infrastructure for making this easier is really important.
