# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


"""Fillmore is a Python library for scrubbing Sentry events."""

from importlib.metadata import (
    version as importlib_version,
    PackageNotFoundError,
)

try:
    __version__ = importlib_version("fillmore")
except PackageNotFoundError:
    __version__ = "unknown"


SCRUBBER_MODULE_NAME = __name__
