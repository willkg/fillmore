from contextlib import contextmanager
from typing import Any, Callable, Dict, Generator, List

import sentry_sdk
from sentry_sdk.transport import Transport


class CaptureTransport(Transport):
    def __init__(self, capture_event_callback: Callable) -> None:
        Transport.__init__(self)
        self.capture_event: Callable = capture_event_callback
        self.capture_envelope: Callable = lambda *args, **kwargs: None
        self._queue = None


class SentryTestHelper:
    """Sentry test helper for initializing Sentry and capturing events.

    This lets you access the events emitted via the ``.events`` attribute.

    """

    def __init__(self) -> None:
        self.events: List[Dict[Any, Any]] = []

    def capture_event(self, event: Dict[Any, Any]) -> None:
        self.events.append(event)

    @contextmanager
    def session_context(self) -> Generator["SentryTestHelper", None, None]:
        self.events = []
        with sentry_sdk.Hub(None):
            yield self

    def init(self, *args: Any, **kwargs: Any) -> None:
        """Use the args for sentry_sdk.Client"""
        self.events = []
        hub = sentry_sdk.Hub.current
        client = sentry_sdk.Client(*args, **kwargs)
        hub.bind_client(client)
        client.transport = CaptureTransport(self.capture_event)
