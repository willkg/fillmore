# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from fillmore.test import SentryTestHelper


@pytest.fixture
def sentry_helper() -> SentryTestHelper:
    """SentryTestHelper fixture

    This creates a helper and sets up the context so it's usable immediately.

    """
    return SentryTestHelper()
