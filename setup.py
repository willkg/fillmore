#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


import os
import re
from setuptools import find_packages, setup


def get_version():
    fn = os.path.join("src", "fillmore", "__init__.py")
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
    name="fillmore",
    version=get_version(),
    description="Sentry event scrubber and utilities library",
    long_description=(get_file("README.rst") + "\n\n" + get_file("HISTORY.rst")),
    long_description_content_type="text/x-rst",
    author="Will Kahn-Greene",
    author_email="willkg@mozilla.com",
    url="https://github.com/willkg/fillmore",
    install_requires=INSTALL_REQUIRES,
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    license="MPLv2",
    zip_safe=False,
    keywords="sentry scrubber",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    project_urls={
        "Documentation": "https://fillmore.readthedocs.io/",
        "Tracker": "https://github.com/willkg/fillmore/issues",
        "Source": "https://github.com/willkg/fillmore/",
    },
    entry_points={
        "pytest11": ["fillmore=fillmore.pytest_plugin"],
    },
    options={"bdist_wheel": {"universal": "1"}},
)
