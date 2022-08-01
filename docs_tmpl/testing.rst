=======
Testing
=======

.. contents::
   :local:


What do you need to test?
=========================

With my applications, I need to verify the following things:

1. Is my application configured correctly?
2. Does Sentry send events when errors are kicked up in various critical parts
   of my application?
3. Are the Sentry events scrubbed correctly?
4. Does scrubbing Sentry events kick up errors?
5. Has the shape of the event that Sentry sends changed because of a change in
   integrations, sentry-sdk client upgrade, or something else?

That results in a few different kinds of tests I run.

* In local testing and CI:

  * Integration tests to verify that Sentry is configured correctly, scrubbing
    works, and the shape of the Sentry event hasn't changed since last time
    I examined it.

* In production:

  * A way to trigger a Sentry event to verify that Sentry is configured
    correctly and events reach the Sentry server.


Integration testing with SentryTestHelper
=========================================

Fillmore provides a ``SentryTestHelper`` to make it convenient to create new or
reuse existing Sentry clients in a way that overrides the transport allowing
you to inspect and assert things against Sentry events that were emitted.

The helper provides two ways to use it:

* :py:func:`fillmore.test.SentryTestHelper.init` a new Sentry client with
  provided parameters
* OR, :py:func:`fillmore.test.SentryTestHelper.reuse` an existing Sentry
  client that was configured in your application code

Both of those create new contexts and clear the event list. You can create
multiple contexts in a single test.

Calling *init* or *reuse* returns an object that keeps track of what events
were emitted and stores them as a list in the ``.events`` property.

Here's an example test using ``unittest``:

.. code-block:: python

   [[[cog
   import cog
   with open("examples/myapp/myapp/test_app.py", "r") as fp:
       cog.outl(fp.read().strip())
   ]]]
   [[[end]]]


Fillmore also provides a `pytest <https://docs.pytest.org/en/7.1.x/>`__ fixture.

Here's an example test using pytest:

.. code-block:: python

   [[[cog
   import cog
   with open("examples/myapp_pytest/myapp/test_app.py", "r") as fp:
       cog.outl(fp.read().strip())
   ]]]
   [[[end]]]


Integration testing against Kent--a fakesentry service
======================================================

`Kent <https://github.com/willkg/kent>`__ is a service that you can run in CI
or on your development machine which can accept Sentry event submissions and
has an API to let you programmatically examine them.

Because Kent is keeping the entire event payload, you know exactly what got
sent and you can hone your scrubbing accordingly.

This lets you write integration tests that run in CI in an environment that has
multiple services.

For example, if you set Kent up at ``http://public@localhost:8090/0`` and you
had ``SENTRY_DSN`` set to that dsn, then you could access it like this:

.. code-block:: python

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
       with sentry_helper.reuse() as sentry_client:
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


Check logging for errors
========================

If Fillmore raised an exception when scrubbing, it'll log a message to the
``fillmore`` logger. 

Your tests should assert that there are no messages at ``logging.ERROR`` level
logged from the ``fillmore`` logger.


Test module API
===============

.. automodule:: fillmore.test
   :members:
