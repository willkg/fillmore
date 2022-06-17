import pytest


# If Django isn't installed, skip tests in this module
django = pytest.importorskip("django")
