#!/bin/sh

# This script is intended to be run under a "manylinux" Docker distribution for building
# Python wheels.

if [ -z "$PLAT" ]; then
    echo No manylinux platform was defined in \$PLAT
    exit 1
fi

set -e
set -x

python -m build
