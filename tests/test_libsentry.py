import pytest

from francis.libsentry import get_sentry_base_url


@pytest.mark.parametrize(
    "url, expected",
    [
        ("http://localhost/0", "http://localhost/"),
        ("http://localhost:8000/0", "http://localhost:8000/"),
        ("http://foo:bar@localhost:8000/0", "http://localhost:8000/"),
    ]
)
def test_get_sentry_base_url(url, expected):
    assert get_sentry_base_url(url) == expected
