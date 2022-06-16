# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import importlib
import json
import logging
from pathlib import Path
from urllib.parse import parse_qsl, urlencode
import uuid
from typing import Any, Callable, Generator, List, Union

import attrs


logger = logging.getLogger(__name__)


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

    If the specified params is ALL_COOKIE_KEYS, then this will filter all cookie values.

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

    If the params is ALL_QUERY_STRING_KEYS, then this will drop the query_string
    altogether.

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
                if val:
                    val = MASK_TEXT
                    has_scrubbed_item = True
            scrubbed_pairs.append((name, val))

        if not has_scrubbed_item:
            return value

        return urlencode(scrubbed_pairs)

    return _scrub_query_string


def str2list(s: str) -> List[str]:
    return s.split(".")


class ScrubRuleError(Exception):
    pass


def thing2fun(thing: Union[Callable, str]) -> Callable:
    """Convert str or Callable to a Callable

    If the thing refers to a scrub function in this module, return that.

    If the thing is a dotted Python path to some other function, return that.

    :raise ScrubRuleError: if the thing is not a callable or does not exist

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
            except AttributeError:
                raise ScrubRuleError(f"{thing} does not exist")

            if callable(fn):
                return fn

    raise ScrubRuleError(f"{thing} is not a callable or a string or does not exist")


@attrs.define
class ScrubRule:
    """

    ``key_path`` is a Python dotted path of key names with ``[]`` to denote
    arrays to traverse pointing to a dict with values to scrub.

    ``keys`` is a list of keys to scrub values of

    ``scrub_function`` is a callable that takes a value and returns a scrubbed value.
    For example::

        def hide_letter_a(value>: str) -> str:
            return "".join([letter if letter != "a" else "*" for letter in value])


    ScrubRule example::

        ScrubRule(
            key_path="request.data",
            keys=["csrfmiddlewaretoken"],
            scrub_function=scrub,
        )

        ScrubRule(
            key_path="request.data",
            keys=["csrfmiddlewaretoken"],
            scrub_function="somemodule.scrubfunction",
        )


    """

    key_path: List[str] = attrs.field(converter=str2list)
    keys: List[str]
    scrub_function: Callable = attrs.field(converter=thing2fun)


SCRUB_RULES_DEFAULT: List[ScrubRule] = [
    # Hide stacktrace variables
    ScrubRule(
        key_path="exception.values.[].stacktrace.frames.[].vars",
        keys=["username", "password"],
        scrub_function=scrub,
    ),
]


def get_target_dicts(event: dict, key_path: List[str]) -> Generator[dict, None, None]:
    """Given a key_path, yields the target dicts.

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

    Example key_path values::

        ["request"]
        ["exception", "stacktrace", "frames", "[]", "vars"]

    """
    parent = event
    for i, part in enumerate(key_path):
        if part == "[]" and isinstance(parent, (tuple, list)):
            for item in parent:
                yield from get_target_dicts(item, key_path[i + 1 :])
            return

        elif part in parent:
            parent = parent[part]

    if isinstance(parent, dict):
        yield parent


def log_exception(msg: str) -> None:
    logger.exception(msg)


class Scrubber:
    """Scrubber pipeline for Sentry events

    https://docs.sentry.io/platforms/python/configuration/filtering/

    """

    def __init__(
        self,
        scrub_rules: List[ScrubRule] = SCRUB_RULES_DEFAULT,
        error_handler: Callable = log_exception,
    ):
        """
        :arg scrub_keys: list of ScrubRule instances

        """
        self.scrub_rules = scrub_rules
        self.error_handler = error_handler

    def __call__(self, event: dict, hint: Any) -> dict:
        """Implements before_send function interface and scrubs Sentry event

        This tries really hard to be very defensive such that even if there are bugs in
        the scrubs, it still emits something to Sentry.

        It will log errors, so we should look for those log statements. They'll all have
        "LIBSENTRYERROR" in the message making them easy to find regardless of the
        logger name.

        Further, they emit two incr metrics:

        * scrub_fun_error
        * get_target_dicts_error

        Put those in a dashboard with alerts so you know when to look in the logs.

        """

        for rule in self.scrub_rules:
            try:
                for parent in get_target_dicts(event, rule.key_path):
                    if not parent:
                        continue

                    for key in rule.keys:
                        if key not in parent:
                            continue

                        val = parent[key]

                        try:
                            filtered_val = rule.scrub_function(val)
                        except Exception as inner_exc:
                            msg = f"scrub fun error: {rule.scrub_function}, error: {inner_exc}"
                            log_exception(msg)
                            try:
                                self.error_handler(msg)
                            except Exception:
                                log_exception("error in error_handler")

                            filtered_val = "ERROR WHEN SCRUBBING"

                        parent[key] = filtered_val

            except Exception as outer_exc:
                msg = f"scrubber error: error: {outer_exc}"
                log_exception(msg)
                try:
                    self.error_handler(msg)
                except Exception:
                    log_exception("error in error_handler")

        return event


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

    Usage:

        scrubber = Scrubber()
        scrubber = SaveEvents(wrapped_scrubber=scrubber, outputdir="/some/path")

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
            log_exception(f"error in SaveEvents.__call__: {exc}")

        return self.wrapped_scrubber(event=event, hint=hint)
