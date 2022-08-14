#!/bin/sh
set -e
src="wastedyears tests"
pyflakes $src
mypy --check-untyped-defs $src
pytest -q --color=no tests
pycodestyle --max-line=90 $src
