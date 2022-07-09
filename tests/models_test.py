from wyr import models


def test_split_description():
    tests = [
        ('foo bar hello    ', ['bar', 'foo', 'hello']),
        ('   foo   bar hello', ['bar', 'foo', 'hello']),
        ('foo, bar, baz', ['bar', 'baz', 'foo']),
        ('foo, bar, & http://example.com?q=x', ['bar', 'foo', 'http://example.com?q=x']),
    ]

    for (input, expect) in tests:
        assert models.split_description(input) == expect
