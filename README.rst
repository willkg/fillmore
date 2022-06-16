.. NOTE: Make sure to edit the template for this file in docs_tmpl/ and
.. not the cog-generated version.

=======
Francis
=======

The Python sentry-sdk has a before_send hook that lets you scrub Sentry events
before they're sent. Francis makes it easier to set up a before_send scrubber
and test it.

:Code:          https://github.com/willkg/francis
:Issues:        https://github.com/willkg/francis/issues
:License:       MPL v2
:Documentation: https://francis.readthedocs.io/


Goals
=====

Goals of Francis:

1. flexible configuration for sentry event scrubbing code that is easy
   to reason about
2. easy to test your scrubbing code

From that, Francis has the following features:

* lets you specify keys to include/exclude from the sentry event
* resilient to errors--if it fails, it will emit a signal that you can see and
  alert on
* links to relevant Sentry documentation, projects, and other things


Install
=======

Run::

    $ pip install francis


Quickstart
==========

FIXME


Why this? Why not other libraries?
==================================

It took me a long while to figure out the shape of the API I needed to scrub
sensitive data from a crash reporting system I work on. There's only one other
library that I found that has a similar-ish purpose, but it was missing some
critical things and wasn't actively maintained.
