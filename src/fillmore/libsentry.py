# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Utility functions for setting up Sentry."""

import logging
from typing import Any, Callable, List, Optional

import sentry_sdk
from sentry_sdk.integrations.logging import ignore_logger

from fillmore import SCRUBBER_MODULE_NAME


logger = logging.getLogger(__name__)


def set_up_sentry(
    sentry_dsn: str,
    release: str,
    host_id: str,
    integrations: Optional[List[Any]] = None,
    before_send: Optional[Callable] = None,
    **kwargs: Any,
) -> None:
    """Set up Sentry

    By default, this will set up default integrations
    (https://docs.sentry.io/platforms/python/configuration/integrations/default-integrations/),
    but not the auto-enabling ones.

    :param sentry_dsn: the Sentry DSN
    :param release: the release name to tag events with
    :param host_id: some str representing the host this service is running on
    :param integrations: list of sentry integrations to set up;
    :param before_send: set this to a callable to handle the Sentry before_send hook

        For scrubbing, do something like this::

            scrubber = Scrubber(rules=SCRUB_RULES_DEFAULT + my_scrub_rules)

        and then pass that as the ``before_send`` value.

    :param kwargs: any additional arguments to pass to sentry_sdk.init()

    """
    if not sentry_dsn:
        return

    sentry_sdk.init(
        dsn=sentry_dsn,
        release=release,
        send_default_pii=False,
        server_name=host_id,
        # This prevents Sentry from trying to enable all the auto-enabling
        # integrations. We only want the ones we explicitly set up. This
        # prevents sentry from loading the Falcon integration (which fails) in a Django
        # context.
        auto_enabling_integrations=False,
        integrations=integrations or [],
        before_send=before_send or None,
        **kwargs,
    )

    # Ignore logging from this module
    ignore_logger(SCRUBBER_MODULE_NAME)
