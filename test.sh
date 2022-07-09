#!/bin/sh
set -e
src=wyr
pyflakes $src
mypy --check-untyped-defs --ignore-missing-imports $src
pycodestyle --max-line=90 $src
