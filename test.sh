#!/bin/sh
set -e
src="wyr tests"
pyflakes $src
mypy --check-untyped-defs --ignore-missing-imports $src
pytest -q --color=no tests
pycodestyle --max-line=90 $src
