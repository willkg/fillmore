# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from contextlib import contextmanager
from itertools import zip_longest
import json
import logging
from pathlib import Path
from typing import Any, Dict, Generator, List
from unittest.mock import ANY, patch
from urllib.parse import urlparse
import uuid

import sentry_sdk
from sentry_sdk.transport import Transport

from fillmore.scrubber import Scrubber


LOGGER = logging.getLogger(__name__)


def get_sentry_base_url(sentry_dsn: str) -> str:
    """Given a sentry_dsn, returns the base url

    This is helpful for tests that need the url to the fakesentry api.

    :param sentry_dsn: the sentry base url

    :raises TypeError: when sentry_dsn is not a string

    :raises ValueError: when sentry_dsn is empty

    """
    if not isinstance(sentry_dsn, str):
        raise TypeError("sentry_dsn must be a str")

    if not sentry_dsn:
        raise ValueError("sentry_dsn is required")

    parsed_dsn = urlparse(sentry_dsn)
    netloc = parsed_dsn.netloc
    if "@" in netloc:
        netloc = netloc[netloc.find("@") + 1 :]

    return f"{parsed_dsn.scheme}://{netloc}/"


class _CaptureTransport(Transport):
    """Sentry transport that captures emitted events."""

    def __init__(self) -> None:
        Transport.__init__(self)
        self._queue = None

        self.events: List[Dict[Any, Any]] = []

    def capture_event(self, event: Dict[Any, Any]) -> None:
        self.events.append(event)

    def capture_envelope(self, envelope: Any) -> None:
        pass

    def reset(self) -> None:
        self.events = []


class ReuseException(Exception):
    """Raised when there's no sentry_sdk client configured to reuse"""


class SentryTestHelper:
    """Sentry test helper for initializing Sentry and capturing events.

    This helper lets you create new sentry_sdk clients or reuse existing
    configured ones.

    You can access emitted events with the ``.events`` attribute.

    You can reset the event list with ``.reset()``.

    """

    def __init__(self) -> None:
        self._transport = _CaptureTransport()

    @property
    def events(self) -> List[Dict[Any, Any]]:
        """Access the event list."""
        return self._transport.events

    def reset(self) -> None:
        """Resets the event list."""
        self._transport.reset()

    @contextmanager
    def init(
        self, *args: Any, **kwargs: Any
    ) -> Generator["SentryTestHelper", None, None]:
        """Create a new sentry_sdk client with specified args

        This creates a new sentry_sdk client with the specified args and
        patches the client transport with one that captures Sentry events that
        are being emitted. This lets you assert things against events.

        Arguments are the same as to ``sentry_sdk.Client``.

        .. seealso::

           https://docs.sentry.io/platforms/python/configuration/options/

        """
        with sentry_sdk.Hub(None):
            hub = sentry_sdk.Hub.current
            client = sentry_sdk.Client(*args, **kwargs)
            hub.bind_client(client)

            self._transport.reset()
            client.transport = self._transport
            yield self

    @contextmanager
    def reuse(self) -> Generator["SentryTestHelper", None, None]:
        """Re-use the current sentry_sdk client, but patch the transport

        This clears the breadcrumbs of the current sentry_sdk scope and patches
        the client transport with one that captures Sentry events that are
        being emitted. This lets you assert things against events.

        :raises ReuseException: if there's no sentry client initialized

        """
        client = sentry_sdk.Hub.current.client
        if not client:
            raise ReuseException("there is no client to reuse")

        self._transport.reset()

        # Clear the breadcrumbs in the scope
        sentry_sdk.Hub.current.scope.clear_breadcrumbs()

        # Mock the transport with one that captures events
        with patch.object(client, attribute="transport", new=self._transport):
            yield self


class ConfigurationError(Exception):
    pass


class SaveEvents:
    """Utility wrapper for saving Sentry events to files on disk.

    This is for collecting Sentry event data to build tests to verify scrubbing
    is working as you need it to.

    .. Note::

       Capturing Sentry event data and writing tests against that is fragile
       and not as good as writing integration tests that kick up Sentry events
       that then get scrubbed.

       Make sure to update captured data periodically. This will avoid skew
       from sentry_sdk updates where they change the shape of the events or
       what's included in events as well as changes to your code which changes
       frame-local vars, context data, and so on.

    Usage::

        scrubber = Scrubber( ... )
        scrubber = SaveEvents(
            wrapped_scrubber=scrubber,
            outputdir="/some/path"
        )

    """

    def __init__(self, wrapped_scrubber: Scrubber, outputdir: str):
        self.wrapped_scrubber = wrapped_scrubber
        self.outputdir = Path(outputdir)
        if not self.outputdir.is_dir():
            raise ConfigurationError(f"outputdir {outputdir} does not exist")

    def __call__(self, event: dict, hint: Any) -> dict:
        try:
            event_id = uuid.uuid4().hex
            path = self.outputdir / f"{event_id}.json"
            data = json.dumps(event)
            path.write_text(data)
        except Exception as exc:
            LOGGER.exception(f"error in SaveEvents.__call__: {exc}")

        return self.wrapped_scrubber(event=event, hint=hint)


def diff_event(
    a: Dict[str, Any], b: Dict[str, Any], path: str = ""
) -> List[Dict[str, Any]]:
    """Compares two Sentry event structures.

    This supports ``unittest.mock.ANY`` which will always match.

    Example::

        # Get an event from the SentryTestHelper.events list and diff it
        # against the expected event
        differences = diff_event(event, expected)
        assert differences == []


    :arg a: first structure
    :arg b: second structure

    :returns: list of differences each as a dict with "msg", "a", "b", "path"
        keys

        For example::

            {
                "msg": "different types: a:<class 'int'> b:<class 'str'>",
                "path": "some.path",
                "a": 5,
                "b": "five",
            }

    """
    if a is ANY or b is ANY:
        return []

    if type(a) != type(b):
        return [
            {
                "msg": f"different types a:{type(a)} b:{type(b)}",
                "path": path,
                "a": a,
                "b": b,
            }
        ]

    if isinstance(a, (list, tuple)):
        i = 0
        differences = []
        for item_a, item_b in zip_longest(a, b, fillvalue=None):
            differences.extend(diff_event(item_a, item_b, f"{path}.[{i}]"))
            i += 1
        return differences

    if isinstance(a, dict):
        keyset_a = set(a.keys())
        keyset_b = set(b.keys())
        differences = []

        # Iterate over common keys of both sets
        for key in sorted(keyset_a & keyset_b):
            differences.extend(diff_event(a[key], b[key], f"{path}.{key}"))

        # Print out missing keys
        delta_keys = keyset_a - keyset_b
        if delta_keys:
            for key in sorted(delta_keys):
                differences.append(
                    {
                        "msg": f"{key} in a, not in b",
                        "path": path,
                        "a": a,
                        "b": b,
                    }
                )

        delta_keys = keyset_b - keyset_a
        if delta_keys:
            for key in sorted(delta_keys):
                differences.append(
                    {
                        "msg": f"{key} in b, not in a",
                        "path": path,
                        "a": a,
                        "b": b,
                    }
                )
        return differences

    if isinstance(a, (int, float, str)):
        if a != b:
            return [
                {
                    "msg": f"{a!r} != {b!r}",
                    "path": path,
                    "a": a,
                    "b": b,
                }
            ]

    return []
