# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import importlib
import logging
from urllib.parse import parse_qsl, urlencode
from typing import Any, Callable, Generator, List, Optional, Union

import attrs


LOGGER = logging.getLogger(__name__)


MASK_TEXT: str = "[Scrubbed]"


ALL_COOKIE_KEYS: Any = object()
ALL_QUERY_STRING_KEYS: Any = object()


def scrub(value: str) -> str:
    """Scrub a value"""
    return MASK_TEXT


def build_scrub_cookies(params: List[str]) -> Callable:
    """Scrub specified keys in HTTP request cookies

    Sentry says the cookies can be:

    * an unparsed string
    * a dictionary
    * a list of tuples

    For the unparsed string, this parses it and figures things out.

    For dictionary and list of tuples, this returns the scrubbed forms of those.

    If the specified params is ``ALL_COOKIE_KEYS``, then this will scrub all
    cookie values.

    """

    def _scrub_cookies(value: Union[str, dict, list]) -> Union[str, dict, list]:
        to_scrub = params

        if not value:
            return value

        if isinstance(value, dict):
            if to_scrub is ALL_COOKIE_KEYS:
                value = {key: MASK_TEXT for key in value.keys()}
                return value

            for param in to_scrub:
                if param in value:
                    value[param] = MASK_TEXT
            return value

        if isinstance(value, list):
            if to_scrub is ALL_COOKIE_KEYS:
                value = [(pair[0], MASK_TEXT) for pair in value]
                return value

            for i, pair in enumerate(value):
                if pair[0] in to_scrub:
                    value[i] = (pair[0], MASK_TEXT)
            return value

        has_scrubbed_item = False
        scrubbed_pairs = []
        for cookie in value.split(";"):
            name, val = cookie.split("=", 1)
            name = name.strip()
            val = val.strip()

            if to_scrub is ALL_COOKIE_KEYS or name in to_scrub:
                if val:
                    val = MASK_TEXT
                    has_scrubbed_item = True
            scrubbed_pairs.append((name, val))

        if not has_scrubbed_item:
            return value

        return "; ".join(["=".join(pair) for pair in scrubbed_pairs])

    return _scrub_cookies


def build_scrub_query_string(params: List[str]) -> Callable:
    """Scrub specified keys in an HTTP request query_string

    Sentry says the query_string can be:

    * an unparsed string
    * a dictionary
    * a list of tuples

    For the unparsed string, this parses it and figures things out. If there's nothing
    that needs to be scrubbed, then it returns the original string. Otherwise it
    returns a query_string value with the items scrubbed, and reformed into a
    query_string. This sometimes means that other things in the string have changed and
    that may make debugging issues a little harder.

    For dictionary and list of tuples, this returns the scrubbed forms of those.

    If the params is ``ALL_QUERY_STRING_KEYS``, then this will scrub all
    query_string values.

    .. Note::

       The Sentry docs say that the query_string could be part of the url. This doesn't
       handle that situation.

    """

    def _scrub_query_string(value: Union[str, list, dict]) -> Union[str, list, dict]:
        to_scrub = params
        if not value:
            return value

        if isinstance(value, dict):
            if to_scrub is ALL_QUERY_STRING_KEYS:
                value = {key: MASK_TEXT for key in value.keys()}
                return value

            for param in to_scrub:
                if param in value:
                    value[param] = MASK_TEXT
            return value

        if isinstance(value, list):
            if to_scrub is ALL_QUERY_STRING_KEYS:
                value = [(pair[0], MASK_TEXT) for pair in value]
                return value

            for i, pair in enumerate(value):
                if pair[0] in to_scrub:
                    value[i] = (pair[0], MASK_TEXT)
            return value

        has_scrubbed_item = False
        scrubbed_pairs = []
        for name, val in parse_qsl(value, keep_blank_values=True):
            if to_scrub is ALL_QUERY_STRING_KEYS or name in to_scrub:
                val = MASK_TEXT
                has_scrubbed_item = True
            scrubbed_pairs.append((name, val))

        if not has_scrubbed_item:
            return value

        return urlencode(scrubbed_pairs)

    return _scrub_query_string


def str2list(s: str) -> List[str]:
    """Splits a string into parts using "." as the separator"""
    return s.split(".")


class RuleError(Exception):
    pass


def thing2fun(thing: Union[Callable, str]) -> Callable:
    """Convert str or Callable to a Callable

    If the thing refers to a scrub function in this module, return that.

    If the thing is a dotted Python path to some other function, return that.

    :raise RuleError: if the thing is not a callable or does not exist

    """
    if callable(thing):
        return thing

    if isinstance(thing, str):
        if thing in globals():
            # If it's global in this module, then pull that
            fn = globals()[thing]
            if callable(fn):
                return fn

        elif "." in thing:
            module_name, class_name = thing.rsplit(".", 1)
            module = importlib.import_module(module_name)
            try:
                fn = getattr(module, class_name)
            except AttributeError as exc:
                raise RuleError(f"{thing} does not exist") from exc

            if callable(fn):
                return fn

    raise RuleError(f"{thing} is not a callable or a string or does not exist")


@attrs.define
class Rule:
    """

    :param path: Python dotted path of key names with ``[]`` to denote
        arrays to traverse pointing to a dict with values to scrub.

    :param keys: list of keys to scrub values of

    :param scrub: is a callable that takes a value and returns a scrubbed value.
        For example:

        .. code-block::

           def hide_letter_a(value>: str) -> str:
               return "".join([letter if letter != "a" else "*" for letter in value])


    Rule example::

        Rule(
            path="request.data",
            keys=["csrfmiddlewaretoken"],
            scrub=scrub,
        )

        Rule(
            path="request.data",
            keys=["csrfmiddlewaretoken"],
            scrub="somemodule.scrubfunction",
        )

    """

    path: List[str] = attrs.field(converter=str2list)
    keys: List[str]
    scrub: Callable = attrs.field(converter=thing2fun)


SCRUB_RULES_DEFAULT: List[Rule] = [
    # Hide "username" and "password" in stacktrace frame-local vars
    Rule(
        path="exception.values.[].stacktrace.frames.[].vars",
        keys=["username", "password"],
        scrub=scrub,
    ),
]


class RulePathError(Exception):
    """The rule path doesn't match the structure of the event"""


def _get_target_dicts(event: dict, path: List[str]) -> Generator[dict, None, None]:
    """Given a path, yields the target dicts.

    Keys should be dict keys. To traverse all the items in an array value, use ``[]``.

    With this event::

        {
            "request": { ... },
            "exception": {
                "stacktrace": {
                    "frames": [
                        {"name": "frame1", "vars": { ... }},
                        {"name": "frame2", "vars": { ... }},
                        {"name": "frame3", "vars": { ... }},
                        {"name": "frame4", "vars": { ... }},
                    ]
                }
            }
        }

    Example path values::

        ["request"]
        ["exception", "stacktrace", "frames", "[]", "vars"]

    """
    parent = event
    for i, part in enumerate(path):
        if part == "[]":
            if not isinstance(parent, (tuple, list)):
                # FIXME(willkg): raising an issue here means that this rule is
                # misconfigured but we don't end up scrubbing anything, so it
                # could result in leaked data and that seems bad
                partial_path = ".".join(path[0 : i + 1])
                raise RulePathError(
                    f"path {partial_path!r} doesn't match event structure"
                )

            for item in parent:
                yield from _get_target_dicts(item, path[i + 1 :])
            return

        elif part in parent:
            parent = parent[part]

        else:
            # This path doesn't point to a thing in the structure
            return

    if isinstance(parent, dict):
        yield parent


class Scrubber:
    """Scrubber pipeline for Sentry events

    This is used as a ``before_send`` value as discussed here:

    https://docs.sentry.io/platforms/python/configuration/filtering/

    You create a :py:class:`fillmore.scrubber.Scrubber` with a list of scrub
    rules. When sentry_sdk is about to emit an event, the
    :py:class:`fillmore.scrubber.Scrubber` applies the scrub rules to the event
    and returns the scrubbed event data.

    If a scrub rule kicks up an error, then the configured ``error_handler`` is
    called.

    """

    def __init__(
        self,
        rules: List[Rule] = SCRUB_RULES_DEFAULT,
        error_handler: Optional[Callable] = None,
    ):
        """
        :param rules: list of Rule instances
        :param error_handler: function that takes a msg (str) and is called
            when either a scrub rule or getting the specified key by path in the
            Sentry event kicks up an error; this lets you emit some kind of signal
            when the Sentry scrubbing code is failing so it doesn't do it silently.

            By default, this logs an exception.

        """
        self.rules = rules
        self.error_handler = error_handler

    def __call__(self, event: dict, hint: Any) -> dict:
        """Implements before_send function interface and scrubs Sentry event

        This tries really hard to be very defensive such that even if there are bugs in
        the scrubs, it still emits something to Sentry.

        It will log errors, so we should look for those log statements. They'll
        all be coming from the "fillmore.scrubber" logger.

        """

        for rule in self.rules:
            try:
                for parent in _get_target_dicts(event, rule.path):
                    if not parent:
                        continue

                    for key in rule.keys:
                        if key not in parent:
                            continue

                        val = parent[key]

                        try:
                            filtered_val = rule.scrub(val)
                        except Exception as inner_exc:
                            msg = f"scrub fun error: {rule.scrub.__name__}, error: {inner_exc}"
                            LOGGER.exception(msg)
                            if self.error_handler is not None:
                                try:
                                    self.error_handler(msg)
                                except Exception:
                                    LOGGER.exception(
                                        f"error in error_handler {self.error_handler.__name__}"
                                    )

                            filtered_val = "ERROR WHEN SCRUBBING"

                        parent[key] = filtered_val

            except Exception as outer_exc:
                msg = f"scrubber error: error: {outer_exc}"
                LOGGER.exception(msg)
                if self.error_handler is not None:
                    try:
                        self.error_handler(msg)
                    except Exception:
                        LOGGER.exception(
                            f"error in error_handler {self.error_handler.__name__}"
                        )

        return event
