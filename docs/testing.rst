=======
Testing
=======

.. contents::
   :local:


Integration testing
===================

You can set up your application to send Sentry events to a Sentry server and
then inspect the events on the server.

Each event lets you download the event data as JSON.

The event data on the Sentry server isn't the exact same shape as the Sentry
event being sent by the client, so this can be a little difficult to work with.


Integration testing with Kent
=============================

`Kent <https://github.com/willkg/kent>`__ is a service that you can run in CI
or on your development machine which can accept Sentry event submissions and
has an API to let you programmatically examine them.

Because Kent is keeping the entire event payload, you know exactly what got
sent and you can hone your scrubbing accordingly.

This lets you write integration tests that run in CI.

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


   def test_sentry():
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


Other tests
===========

Fillmore comes with some testing helpers including a pytest fixture.

For example, here's a pytest test that uses ``sentry_helper`` pytest fixture to
test a Django view that intentionally kicks up an exception and asserts
scrubbing outcomes:

.. code-block:: python

   from sentry_sdk.integrations.django import DjangoIntegration
   # Use the werkzeug wsgi client because the Django test client fakes
   # everything
   from werkzeug.test import Client

   from myapp.wsgi import application


   def test_sentry(sentry_helper):
       client = Client(application)
       kwargs = {
           "auto_enabling_integrations": False,
           "integrations": [DjangoIntegration()],
       }

       # init initializes a new Sentry client with whatever parameters you
       # specify
       with sentry_helper.init(**kwargs) as sentry_client:
           resp = client.get("/broken")
           assert resp.status_code == 500

           (event,) = sentry_client.events

           assert "django" in event["sdk"]["integrations"]
           assert "request" in event
           assert event["request"]["headers"]["Auth-Token"] == "[Scrubbed]"


However, what if your Django application already sets up a Sentry client? Then
you would want to reuse it the client, but in a way that lets you capture the
events it would send out so you can assert things against them:

.. code-block:: python

   from werkzeug.test import Client

   from myapp.wsgi import application


   def test_sentry(sentry_helper):
       client = Client(application)

       # reuse uses an existing configured Sentry client, but mocks the
       # transport so you can assert things against the Sentry events 
       # generated
       with sentry_helper.reuse() as sentry_client:
           resp = client.get("/broken")
           assert resp.status_code == 500

           (event,) = sentry_client.events

           assert "django" in event["sdk"]["integrations"]
           assert "request" in event
           assert event["request"]["headers"]["Auth-Token"] == "[Scrubbed]"


pytest fixture
==============

Fillmore includes a pytest fixture to make using the
:py:class:`fillmore.test.SentryTestHelper` a little easier.

.. code-block:: python

   from werkzeug.test import Client

   from myapp.wsgi import application


   def test_sentry(sentry_helper):
       client = Client(application)

       # reuse uses an existing configured Sentry client, but mocks the
       # transport so you can assert things against the Sentry events 
       # generated
       with sentry_helper.reuse() as sentry_client:
           resp = client.get("/broken")
           assert resp.status_code == 500

           (event,) = sentry_client.events

           assert "django" in event["sdk"]["integrations"]
           assert "request" in event
           assert event["request"]["headers"]["Auth-Token"] == "[Scrubbed]"


Test module API
===============

.. automodule:: fillmore.test
   :members:
