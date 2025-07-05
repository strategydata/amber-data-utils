import pytest
from amber_data_utils.url_utils import (
    update_param
)

@pytest.mark.parametrize(
    "url,param_name,new_value,expected",
    [
        (
            "https://example.com/path?foo=1&bar=2",
            "foo",
            42,
            "https://example.com/path?foo=42&bar=2"
        ),
        (
            "https://example.com/path",
            "newparam",
            "hello",
            "https://example.com/path?newparam=hello"
        ),
        (
            "https://example.com/path?x=100",
            "x",
            "200",
            "https://example.com/path?x=200"
        ),
        (
            "https://example.com/path?x=1&y=2&y=3",
            "y",
            "99",
            "https://example.com/path?x=1&y=99"
        ),
        (
            "https://example.com/path?foo=1#section2",
            "foo",
            "bar",
            "https://example.com/path?foo=bar#section2"
        ),
        (
            "https://example.com/path?foo=1&bar=2",
            "baz",
            "3",
            "https://example.com/path?foo=1&bar=2&baz=3"
        ),
    ]
)
def test_update_param(url, param_name, new_value, expected):
    result = update_param(url, param_name, new_value)
    assert result == expected