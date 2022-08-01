#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Run tests in examples/ directoriies.

# Run the myapp test which will detect Python syntax errors, import
# errors, and verifies the test works
echo ">>> running examples/myapp/ tests"
pushd myapp
python -m unittest discover
popd

echo ">>> running examples/myapp_pytest/ tests"
pytest myapp_pytest

# Run the file which will detect Python syntax errors and import
# errors
echo ">>> running examples/scrubber/ tests"
pushd scrubber
python webapp_scrubber.py
python fillmore_logging.py
popd
