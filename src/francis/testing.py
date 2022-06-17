from contextlib import contextmanager

import sentry_sdk
from sentry_sdk.transport import Transport


class CaptureTransport(Transport):
    def __init__(self, capture_event_callback):
        Transport.__init__(self)
        self.capture_event = capture_event_callback
        self.capture_envelope = lambda *args, **kwargs: None
        self._queue = None


class SentryTestHelper:
    def __init__(self):
        self.events = []

    def capture_event(self, event):
        self.events.append(event)

    @contextmanager
    def session_context(self):
        self.events = []
        with sentry_sdk.Hub(None):
            yield self

    def init(self, *args, **kwargs):
        self.events = []
        hub = sentry_sdk.Hub.current
        client = sentry_sdk.Client(*args, **kwargs)
        hub.bind_client(client)
        client.transport = CaptureTransport(self.capture_event)
