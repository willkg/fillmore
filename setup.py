#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import os
import re
from setuptools import find_packages, setup


def get_version():
    fn = os.path.join("src", "francis", "__init__.py")
    vsre = r"""^__version__ = ['"]([^'"]*)['"]"""
    version_file = open(fn).read()
    return re.search(vsre, version_file, re.M).group(1)


def get_file(fn):
    with open(fn) as fp:
        return fp.read()


INSTALL_REQUIRES = [
    "attrs>=21.2.0",
    "sentry-sdk>=1.5.0",
]


setup(
    name="francis",
    version=get_version(),
    description="Sentry event scrubber library",
    long_description=(get_file("README.rst") + "\n\n" + get_file("HISTORY.rst")),
    author="Will Kahn-Greene",
    author_email="willkg@mozilla.com",
    url="https://github.com/willkg/francis",
    install_requires=INSTALL_REQUIRES,
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    license="MPLv2",
    zip_safe=False,
    keywords="sentry scrubber",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    project_urls={
        "Documentation": "https://francis.readthedocs.io/",
        "Tracker": "https://github.com/willkg/francis/issues",
        "Source": "https://github.com/willkg/francis/",
    },
    options={"bdist_wheel": {"universal": "1"}},
)
