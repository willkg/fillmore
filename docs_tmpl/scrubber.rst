========
Scrubber
========

.. contents::
   :local:


Quickstart
==========

1. Create a :py:class:`fillmore.scrubber.Scrubber` instance.

2. Pass it a set of :py:class:`fillmore.scrubber.Rule` instances specifying
   things to scrub and how to scrub them.


For example, lets say you wanted to remove the ``Auth-Token`` and
``X-Forwarded-For`` headers, ``code`` and ``state`` cookies, and also any
frame-local variables with the name ``password``.

Example:

.. code-block:: python

   [[[cog
   import cog
   with open("examples/scrubber/webapp_scrubber.py", "r") as fp:
       cog.outl(fp.read().strip())
   ]]]
   [[[end]]]


Things to know about scrubbing:

1. The Scrubber can take any number of rules.
2. Rules are executed in order.
3. If the rule specifies data that doesn't exist in the Sentry event, then the
   rule won't be run.
4. Anything scrubbed by Fillmore scrub functions has the value ``[Scrubbed]``.
   You can distinguish this from things scrubbed by sentry_sdk or Sentry server
   which use ``[Filtered]``.

.. Note::

   If traversing the Sentry event for the data to be scrubbed or the scrub rule
   kicks up an error, Fillmore will log the exception to the
   ``fillmore.scrubber`` logger. Make sure to set up the ``fillmore`` logger
   and set the level to ``logging.ERROR`` when setting up Python logging.


How do I know what data to scrub?
==================================

`Sentry <https://getsentry.com/>`__ maintains documentation on the event
payload as well as a schema.


Capturing Sentry event payloads
-------------------------------

You can set your application up to send data to a "fake sentry" like `Kent
<https://github.com/willkg/kent/>`__ and capture Sentry events to know exactly
what data is getting sent and where in the payload it is.


Sentry event schema
-------------------

The schema for Sentry events is here:

https://github.com/getsentry/sentry-data-schemas/blob/main/relay/event.schema.json

You can validate Sentry event data using that.


Sentry interface docs
---------------------

Here are some interesting sections of the Sentry event:

Breadcrumbs interface
~~~~~~~~~~~~~~~~~~~~~

https://develop.sentry.dev/sdk/event-payloads/breadcrumbs/

Breadcrumbs get added by Sentry integrations capturing various interesting
things that happened before the Sentry event.

To cut down on breadcrumbs, it's best to not include the relevant integrations.

Fillmore lets you scrub breadcrumbs when Sentry events happen, but you might
want to scrub breadcrumbs when they're being captured using a
``before_breadcrumbs`` function.

https://docs.sentry.io/platforms/python/configuration/options/#before-breadcrumb

Breadcrumbs tend to be free form, so Fillmore doesn't have a good scrubber for
them--Fillmore scrubs the whole value or none of it. You'll either want to write
your own scrub function that does what you need or you'll want to write a
``before_breadcrumbs`` function that fixes the breadcrumbs as they're captured.


Contexts interface
~~~~~~~~~~~~~~~~~~

https://develop.sentry.dev/sdk/event-payloads/contexts/

This provides additional data about the environment the error happened in.
Device, operating system, browser, gpu, etc.

If one of the integrations you're using fills in some state context, that might
be something to look into for scrubbing.


Exception interface
~~~~~~~~~~~~~~~~~~~

Exception data:

https://develop.sentry.dev/sdk/event-payloads/exception/

Stack trace data:

https://develop.sentry.dev/sdk/event-payloads/stacktrace/

When Sentry captures unhandled exceptions, the exception information goes in
this interface. It can have multiple stacktraces each of which consists of
a stack of frames and related information.

If your application handles sensitive data that can't go to a Sentry server,
then you should make sure to shut off frame-local vars::

    with_locals=False

Otherwise, each frame can include variable names and values and it's really
hard to scrub that effectively.


Requests interface (for webapps)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

https://develop.sentry.dev/sdk/event-payloads/request/

Some things to know:

1. Different web frameworks capture the query string and cookies differently plus
   those two things can end up in multiple parts of the event.

   cookies
       This is stored in ``request.cookies`` as a string, a list of ``(name,
       value)`` tuples, or a dict.

       It can also show up in ``request.headers.Cookie`` as a string.

       Depending on the integrations used, if you specify::

           send_default_pii=False

       then the cookie data may be an **empty string** regardless of whether
       there is cookie data or not.

   query string
       This is stored in ``request.query_string`` as a string, a list of ``(name,
       value)`` tuples, or a dict.

       It can also show up as a string in the ``request.url`` field value and in
       the repr of request objects in the stacktrace frames local-vars.

2. Request data is in ``request.data`` and may contain anything being submitted
   or uploaded.
   
   If users are submitting forms or uploading sensitive data, you might want
   to consider setting::

        request_bodies="never"

   which will prevent the request data from being in the Sentry event.

   If you want to scrub it, you'll need to handle the fact that it could be
   bytes or a structured format depending on the integrations you have
   installed.

3. Request headers can include tokens, session information, and also
   information about your infrastructure.

   If you set::

       send_default_pii=False

   then many of these headers are not added to the Sentry event. See the
   documentation (and possibly the code) for the integrations you're using.


How do I debug Scrubbing problems?
==================================

If the scrubbing code is kicking up exceptions, then Fillmore will log
exceptions to the ``fillmore`` logger. Make sure to set up Python logging
and set the ``fillmore`` logger to ``logging.ERROR``:

.. code-block:: python

   [[[cog
   import cog
   with open("examples/scrubber/fillmore_logging.py", "r") as fp:
       cog.outl(fp.read().strip())
   ]]]
   [[[end]]]


How does it work?
=================

The Python sentry-sdk generates Sentry events. Before sending the events, it
passes the event to the function specified as the ``before_send`` handler
when initializing Sentry.

The ``before_send`` handler takes the Sentry event and a hint as arguments.

The Fillmore Scrubber runs a series of Scrub Rules on the event producing an
event with specified data scrubbed.

The sentry-sdk then sends this scrubbed event to the Sentry server.

.. seealso::

   Filtering in sentry-sdk docs:
       https://docs.sentry.io/platforms/python/configuration/filtering/

   Scrubbing data in sentry-sdk docs:
       https://docs.sentry.io/platforms/python/data-management/sensitive-data/
