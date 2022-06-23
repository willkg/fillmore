=================
Setting up Sentry
=================

.. contents::
   :local:


Summary
=======

sentry_sdk is very flexible in the way it lets you set up Sentry.


Setting up Sentry with Fillmore's helper
========================================

Fillmore has a helper for setting up Sentry that aims for "least surprising".
This sets the following:

1. Sets ``release`` and ``host_id``.
2. Sets ``send_default_pii=False`` to reduce sensitive information leakage.
3. Sets ``auto_enabling_integrations=False`` so Sentry doesn't try to import
   things and then load the integration if they import. This does mean you need
   to make sure all the integrations you want loaded are specified in
   ``integrations`` argument.
4. Adds the scrubber logger to the ignore logger list so that when Sentry is
   handling an event and the scrubber is scrubbing and logs an exception, that
   doesn't cause Sentry to handle another event which could recurse
   indefinitely and be bad.

You can use it like this:

.. code-block:: python

   from fillmore.libsentry import set_up_sentry
   from fillmore.scrubber import Scrubber, Rule

   dsn = "some dsn"
   release = "some identifier for this release of this app"
   host_id = "some identifier of this host"

   # Explicitly load integrations you approve
   approved_integrations = [
       ...
   ]

   # Set up a scrubber to scrub sensitive data from the Sentry event
   scrubber = Scrubber(
       rules=[
           Rule( ... ),
           Rule( ... ),
       ]
   )

   set_up_sentry(
       sentry_dsn=dsn,
       release=release,
       host_id=host_id,
       integrations=approved_integrations,
       before_send=scrubber,
    )


Setting up Sentry for applications with sensitive data
======================================================

For applications with sensitive information, we're doing something like this:

.. code-block:: python

   from fillmore.libsentry import set_up_sentry
   from fillmore.scrubber import Scrubber, Rule

   dsn = "some dsn"
   release = "some identifier for this release of this app"
   host_id = "some identifier of this host"

   # Explicitly load integrations you approve
   approved_integrations = [
       ...
   ]

   # Set up a scrubber to scrub sensitive data from the Sentry event
   scrubber = Scrubber(
       rules=[
           Rule( ... ),
           Rule( ... ),
       ]
   )

   set_up_sentry(
       sentry_dsn=dsn,
       release=release,
       host_id=host_id,

       # Disable frame-local variables
       with_locals=False,

       # Disable request data from being added to Sentry events
       request_bodies="never",

       # All integrations should be intentionally enabled so you know exactly
       # which are loaded and are adding data to the Sentry event even if
       # there are changes in the sentry_sdk or your application
       default_integrations=False,
       integrations=[approved_integrations],

       # Use a scrubber to remove sensitive data
       before_send=scrubber,
   )
